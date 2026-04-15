"""
监听 STS 存档文件，对比前后状态输出具体事件类型。
事件类型（SaveEvent）：
  FLOOR_CHANGED   : 进入了新楼层/房间
  CARD_PICKED     : 拿牌/跳过了一次选牌
  HP_CHANGED      : 血量变化（战斗结束后才能观测到）
  SCORE_CHANGED   : 评分明显变化（牌组组成改变）
  INITIAL         : 首次加载
"""
import os
import time
import threading
from dataclasses import dataclass, field
from enum import Enum, auto

from core.decoder import decode_save, CHARACTER_FILES, SAVE_DIR


class EventType(Enum):
    INITIAL       = auto()
    FLOOR_CHANGED = auto()
    CARD_PICKED   = auto()
    HP_CHANGED    = auto()
    GENERAL       = auto()   # 其他变化（遗物、金币等）


@dataclass
class SaveState:
    """存档的关键快照，用于与上一次对比"""
    floor_num:          int
    current_room:       str
    current_health:     int
    max_health:         int
    card_choices_count: int          # metric_card_choices 的长度
    monster_list:       list[str]    # 当前剩余怪物队列
    elite_list:         list[str]
    path_per_floor:     list[str]    # metric_path_per_floor
    deck_ids:           list[str]    # 牌组 ID，用于检测牌组变化

    @staticmethod
    def from_data(data: dict) -> "SaveState":
        cards = data.get("cards", [])
        deck = [c.get("id","") if isinstance(c,dict) else str(c) for c in cards]
        return SaveState(
            floor_num          = data.get("floor_num", 0),
            current_room       = data.get("current_room", ""),
            current_health     = data.get("current_health", 0) or 0,
            max_health         = data.get("max_health", 1)     or 1,
            card_choices_count = len(data.get("metric_card_choices", [])),
            monster_list       = list(data.get("monster_list", [])),
            elite_list         = list(data.get("elite_monster_list", [])),
            path_per_floor     = list(data.get("metric_path_per_floor", [])),
            deck_ids           = deck,
        )


@dataclass
class SaveEvent:
    event_type:   EventType
    char:         str
    data:         dict          # 当前完整存档数据
    current:      SaveState
    previous:     SaveState | None = None

    # 便捷属性
    @property
    def floor_changed(self) -> bool:
        return (self.previous is not None and
                self.current.floor_num != self.previous.floor_num)

    @property
    def current_floor_type(self) -> str:
        """M=普通怪 E=精英 B=Boss R=休息 $=商店 ?=事件 T=宝箱"""
        idx = self.current.floor_num - 1
        path = self.current.path_per_floor
        if 0 <= idx < len(path) and path[idx]:
            return str(path[idx])
        return "?"

    @property
    def consumed_monster(self) -> str | None:
        """
        进入新楼层时，通过新旧 monster_list 差集找出当前战斗的怪物。
        怪物消费是 FIFO 的，第一个消失的就是当前正在打的那个。
        """
        if not self.floor_changed or self.previous is None:
            return None
        prev = self.previous.monster_list
        curr = self.current.monster_list
        if len(prev) > len(curr):
            return prev[0]          # 第一个被消费的怪物
        # 列表没缩短但内容不同（列表重置了，比如进入新幕）
        return None

    @property
    def new_card_pick(self) -> dict | None:
        """最新一次选牌记录"""
        choices = self.data.get("metric_card_choices", [])
        return choices[-1] if choices else None


class SaveWatcher:
    def __init__(self, callback, interval: float = 0.5):
        """
        callback(event: SaveEvent): 检测到变化时调用
        """
        self._callback = callback
        self._interval = interval
        self._mtimes:  dict[str, float]     = {}
        self._states:  dict[str, SaveState] = {}
        self._running  = False
        self._thread:  threading.Thread | None = None

    def start(self):
        self._running = True
        path_to_char = self._build_path_map()
        # 初始化时间戳和状态
        for path, char in path_to_char.items():
            if os.path.exists(path):
                self._mtimes[path] = os.path.getmtime(path)
                data = decode_save(path)
                if data:
                    self._states[char] = SaveState.from_data(data)
                    # 触发一次 INITIAL 事件
                    event = SaveEvent(
                        event_type=EventType.INITIAL,
                        char=char, data=data,
                        current=self._states[char],
                        previous=None,
                    )
                    try:
                        self._callback(event)
                    except Exception as e:
                        print(f"[Watcher] initial callback error: {e}")

        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _build_path_map(self) -> dict[str, str]:
        return {
            os.path.join(SAVE_DIR, fn): char
            for char, fn in CHARACTER_FILES.items()
        }

    def _loop(self):
        path_to_char = self._build_path_map()
        while self._running:
            for path, char in path_to_char.items():
                if not os.path.exists(path):
                    continue
                try:
                    mtime = os.path.getmtime(path)
                except OSError:
                    continue

                if mtime <= self._mtimes.get(path, 0) + 0.3:
                    continue

                self._mtimes[path] = mtime
                time.sleep(0.2)   # 等游戏写完文件
                data = decode_save(path)
                if not data:
                    continue

                prev_state = self._states.get(char)
                curr_state = SaveState.from_data(data)
                self._states[char] = curr_state

                event_type = self._classify(prev_state, curr_state)
                event = SaveEvent(
                    event_type=event_type,
                    char=char, data=data,
                    current=curr_state,
                    previous=prev_state,
                )
                try:
                    self._callback(event)
                except Exception as e:
                    print(f"[Watcher] callback error: {e}")

            time.sleep(self._interval)

    @staticmethod
    def _classify(prev: SaveState | None, curr: SaveState) -> EventType:
        if prev is None:
            return EventType.INITIAL
        if curr.floor_num != prev.floor_num:
            return EventType.FLOOR_CHANGED
        if curr.card_choices_count != prev.card_choices_count:
            return EventType.CARD_PICKED
        if curr.current_health != prev.current_health:
            return EventType.HP_CHANGED
        return EventType.GENERAL
