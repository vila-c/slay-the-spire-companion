"""
STS Desktop Pet Companion v2
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))

# Suppress Windows error dialog popups
if sys.platform == "win32":
    import ctypes
    ctypes.windll.kernel32.SetErrorMode(0x8003)

_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug.log")
def _log(msg):
    with open(_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")

# ── 单例锁 ─────────────────────────────────────────────
def _check_single_instance():
    if sys.platform == "win32":
        _check_single_instance._mutex = ctypes.windll.kernel32.CreateMutexW(
            None, False, "Global\\STSCompanionMutex"
        )
        if ctypes.windll.kernel32.GetLastError() == 183:
            sys.exit(0)

_check_single_instance()

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore    import QTimer

from core.watcher        import SaveWatcher, SaveEvent, EventType
from core.scorer         import evaluate, ScoreResult
from core.combat_advisor import (get_upcoming_fights, UpcomingFight,
                                  get_enemy_info, parse_room_type)
from core.decoder        import get_active_save, parse_deck, parse_relics, parse_upgraded_ids
from core.card_advisor   import get_card_advice, CardAdvice
from core.shop_advisor   import get_shop_advice
from core.event_advisor  import get_event_advice, get_event_chat_tip
from core.upgrade_advisor import get_rest_advice
from ui.pet_widget       import PetWidget
from ui.bubble           import BubbleWindow
from ui.chat_bubble      import ChatBubble

LEVEL_NAMES = {
    "Exordium":  "关卡1·塔底",
    "TheCity":   "关卡2·城市",
    "TheBeyond": "关卡3·深处",
    "TheEnd":    "终幕·终局",
}

COMBAT_ROOMS = ("MonsterRoom", "MonsterRoomElite", "MonsterRoomBoss")

COMBAT_STATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
    "combat_state.json")


# ── 纯 ctypes 检测 STS 窗口 ───────────────────────────
from ctypes import wintypes

_ENUM_CB_TYPE = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

def _is_sts_running() -> bool:
    found = [False]
    def _cb(hwnd, _):
        length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
            if "slay the spire" in buf.value.lower():
                found[0] = True
                return False
        return True
    ctypes.windll.user32.EnumWindows(_ENUM_CB_TYPE(_cb), 0)
    return found[0]


class STSCompanion:
    def __init__(self, app: QApplication):
        self._app = app
        self._last_result:       ScoreResult | None  = None
        self._last_char:         str | None           = None
        self._last_data:         dict | None          = None
        self._current_fight:     UpcomingFight | None = None
        self._last_combat_ts:    float                = 0.0
        self._last_combat_state: dict | None          = None
        self._last_room_type:    str                  = ""
        self._last_chat_floor:   int                  = -1
        self._last_act:          int                  = 0
        self._opening_shown:     bool                 = False
        self._last_relics:       list[str]            = []
        self._last_intent_hash:  str                  = ""

        self._pet    = PetWidget(on_click=self._on_pet_click,
                                 on_quit=self._quit,
                                 on_move=self._on_pet_move,
                                 on_toggle=self._toggle_pet)
        self._bubble = BubbleWindow(self._pet)
        self._chat   = ChatBubble(self._pet)
        self._pet_visible = True

        self._watcher = SaveWatcher(callback=self._on_event)
        self._watcher.start()

        # 500ms poll real-time combat state
        self._combat_timer = QTimer()
        self._combat_timer.timeout.connect(self._poll_combat_state)
        self._combat_timer.start(500)

        # 2s poll game process
        self._game_running = False
        self._game_timer = QTimer()
        self._game_timer.timeout.connect(self._poll_game_process)
        self._game_timer.start(2000)

        self._poll_game_process()
        if not self._game_running:
            self._pet.hide()

    # ── 事件入口 ──────────────────────────────────────────
    def _on_event(self, event: SaveEvent):
        QTimer.singleShot(0, lambda: self._handle(event))

    def _handle(self, event: SaveEvent):
        char, data, curr, etype = event.char, event.data, event.current, event.event_type

        try:
            result = evaluate(char, data)
        except Exception as e:
            _log(f"[Scorer] error: {e}"); return

        prev_score        = self._last_result.score if self._last_result else None
        self._last_result = result
        self._last_char   = char
        self._last_data   = data

        room_class   = curr.current_room
        in_combat    = any(r in room_class for r in COMBAT_ROOMS)
        current_fight: UpcomingFight | None = None

        if in_combat:
            fights = get_upcoming_fights(data, max_count=1)
            current_fight = fights[0] if fights else None

        self._current_fight = current_fight

        self._pet.set_character(char)
        self._pet.set_hp_ratio(result.hp / max(result.max_hp, 1))
        self._pet.set_mood(_score_to_mood(result.score, result.alerts,
                                          result.hp / max(result.max_hp, 1)))

        # Opening greeting (once per run)
        if etype == EventType.INITIAL and not self._opening_shown:
            self._opening_shown = True
            self._chat.say_opening(char)
            # Neow advice at floor 0
            if curr.floor_num <= 1:
                # Try to get actual Neow options from combat state
                neow_opts = None
                if self._last_combat_state:
                    neow_opts = self._last_combat_state.get("event_options")
                QTimer.singleShot(3000, lambda c=char, o=neow_opts:
                                  self._chat.say_neow_advice(c, event_options=o))

        # Act transition
        act = data.get("act_num", 1)
        if act != self._last_act and self._last_act > 0:
            self._chat.say_act_transition(act)
        self._last_act = act

        # Relic pickup detection
        current_relics = parse_relics(data)
        if self._last_relics and len(current_relics) > len(self._last_relics):
            new_relics = [r for r in current_relics if r not in self._last_relics]
            for relic in new_relics:
                self._chat.say_relic(relic, char, parse_deck(data))
        self._last_relics = current_relics

        # Chat bubble on room change
        if etype == EventType.FLOOR_CHANGED:
            self._trigger_chat_bubble(char, data, result, room_class, current_fight)

        if self._bubble.is_visible():
            self._refresh_bubble(char, data, result, current_fight)
            if self._last_combat_state:
                self._bubble.update_combat_state(self._last_combat_state)

        if etype == EventType.FLOOR_CHANGED and in_combat:
            self._pet.trigger_alert_animation()

        if (prev_score is not None and
                result.score < prev_score - 12 and
                etype not in (EventType.INITIAL,)):
            self._pet.trigger_alert_animation()

    # ── Refresh info panel ─────────────────────────────────
    def _refresh_bubble(self, char, data, result, current_fight):
        fights    = get_upcoming_fights(data, max_count=3) if data else []
        act_label = _act_label(data) if data else ""
        card_adv  = None
        shop_adv  = None
        event_adv = None
        extreme   = None

        if data and char:
            try:
                deck   = parse_deck(data)
                relics = parse_relics(data)
                upgraded = parse_upgraded_ids(data)
                card_adv = get_card_advice(char, deck, result.floor, relics,
                                           upgraded_ids=upgraded)
            except Exception:
                pass

            room = data.get("current_room", "")

            # Shop advice if in shop
            if "ShopRoom" in room:
                try:
                    shop_adv = get_shop_advice(char, data)
                except Exception:
                    pass

            # Event advice if in event room
            if "EventRoom" in room:
                try:
                    ev_name = ""
                    if self._last_combat_state:
                        ev_name = self._last_combat_state.get("event_name", "")
                    event_adv = get_event_advice(char, data, event_name=ev_name)
                except Exception:
                    pass

            # Extreme tip
            extreme = _generate_extreme_tip(char, data, result)

        self._bubble.update_data(
            char, result,
            act_label=act_label,
            fights=fights,
            current_fight=current_fight,
            card_advice=card_adv,
            shop_advice=shop_adv,
            event_advice=event_adv,
            chat_history=self._chat.get_history(),
            extreme_tip=extreme,
        )

    # ── Chat bubble triggers ─────────────────────────────
    def _trigger_chat_bubble(self, char, data, result, room_class, current_fight):
        room_type = parse_room_type(room_class)
        floor_num = data.get("floor_num", 0)
        # Use floor number to deduplicate (allows same room type on different floors)
        if floor_num == self._last_chat_floor:
            return
        self._last_chat_floor = floor_num
        self._last_room_type = room_type

        ctx = {}
        hp_ratio = result.hp / max(result.max_hp, 1)

        if room_type in ("monster", "elite") and current_fight:
            cf = current_fight
            ctx["enemy_display"] = cf.info.display if cf.info else cf.enemy_name
            ctx["strategy"] = cf.info.strategy if cf.info else "小心应对"
            if cf.info and cf.info.avoid_cards:
                ctx["strategy"] += f"，避免{cf.info.avoid_cards[0]}"
        elif room_type in ("monster", "elite") and not current_fight:
            # Fallback: no fight info from save, try combat_state
            enemy_name = ""
            if self._last_combat_state:
                monsters = self._last_combat_state.get("monsters", [])
                if monsters:
                    name = monsters[0].get("name", "")
                    info = get_enemy_info(name)
                    enemy_name = info.display if info else name
                    ctx["enemy_display"] = enemy_name
                    ctx["strategy"] = info.strategy if info else "小心应对"
            if not enemy_name:
                ctx["enemy_display"] = "未知敌人"
                ctx["strategy"] = "注意观察敌人意图，合理分配格挡和攻击"

        elif room_type == "boss":
            boss_list = data.get("boss_list", [])
            boss_name = boss_list[0] if boss_list else None
            boss_info = get_enemy_info(boss_name) if boss_name else None
            ctx["enemy_display"] = boss_info.display if boss_info else "Boss"
            ctx["advice"] = boss_info.strategy if boss_info else "全力以赴！"

        elif room_type == "shop":
            try:
                adv = get_shop_advice(char, data)
                ctx["gold"] = adv["gold"]
                ctx["shop_advice"] = adv["summary"]
            except Exception:
                ctx["gold"] = data.get("gold", 0)
                ctx["shop_advice"] = "看看有什么好东西"

        elif room_type == "rest":
            # Try to get deck data from combat_state.json for upgrade advice
            deck = []
            if self._last_combat_state and "deck" in self._last_combat_state:
                deck = self._last_combat_state["deck"]
            if not deck:
                # Fallback: read from autosave cards
                cards_raw = data.get("cards", [])
                for c in cards_raw:
                    if isinstance(c, dict):
                        deck.append({
                            "id": c.get("id", ""),
                            "name": c.get("id", ""),
                            "upgraded": c.get("upgrades", 0) > 0,
                            "times_upgraded": c.get("upgrades", 0),
                            "type": "", "rarity": "",
                        })
            if deck:
                ctx["rest_advice"] = get_rest_advice(
                    deck, result.hp, result.max_hp, char)
            elif hp_ratio < 0.5:
                ctx["rest_advice"] = f"血量只有{result.hp}/{result.max_hp}，建议休息回血"
            else:
                ctx["rest_advice"] = "血量还行，可以考虑升级牌"

        elif room_type == "event":
            try:
                ev_name = ""
                if self._last_combat_state:
                    ev_name = self._last_combat_state.get("event_name", "")
                ctx["event_advice"] = get_event_chat_tip(char, data, event_name=ev_name)
            except Exception:
                ctx["event_advice"] = "注意选项，权衡风险和收益！"

        elif room_type == "treasure":
            pass  # Template handles this

        self._chat.say_room(room_type, ctx)

    # ── Click pet → toggle panel ────────────────────────────
    def _on_pet_click(self):
        if self._bubble.is_visible():
            self._bubble.hide_bubble()
            return

        char, data = get_active_save()
        if not char:
            char, data = self._last_char, self._last_data

        if char and data:
            try:
                result = evaluate(char, data)
            except Exception:
                result = self._last_result

            self._last_result = result
            self._last_char   = char
            self._last_data   = data

            fights = get_upcoming_fights(data, max_count=3)
            room_class    = data.get("current_room", "")
            in_combat     = any(r in room_class for r in COMBAT_ROOMS)
            current_fight = (fights[0] if fights and in_combat else None)
            self._current_fight = current_fight

            self._pet.set_character(char)
            self._pet.set_hp_ratio(result.hp / max(result.max_hp, 1))
            self._pet.set_mood(_score_to_mood(result.score, result.alerts,
                                              result.hp / max(result.max_hp, 1)))
            self._refresh_bubble(char, data, result, current_fight)
            if self._last_combat_state:
                self._bubble.update_combat_state(self._last_combat_state)
            self._bubble.show_bubble()
        else:
            from core.scorer import ScoreResult
            dummy = ScoreResult(0,"D","无","❓",[],[],0,1,0,0,0,0,0)
            self._bubble.update_data("IRONCLAD", dummy, act_label="未检测到对局")
            self._bubble.show_bubble()

    # ── 游戏进程监听 ──────────────────────────────────────
    def _poll_game_process(self):
        running = _is_sts_running()

        if running and not self._game_running:
            self._game_running = True
            self._opening_shown = False  # Reset for new game session
            if self._pet_visible:
                self._pet.show()
            _log("Game detected, showing pet")
        elif not running and self._game_running:
            self._game_running = False
            self._bubble.hide_bubble()
            self._pet.hide()
            _log("Game closed, hiding pet")

    # ── 实时战斗轮询 ──────────────────────────────────────
    def _poll_combat_state(self):
        try:
            if not os.path.exists(COMBAT_STATE_PATH):
                return
            mtime = os.path.getmtime(COMBAT_STATE_PATH)
            if mtime <= self._last_combat_ts:
                return
            self._last_combat_ts = mtime
            with open(COMBAT_STATE_PATH, encoding="utf-8") as f:
                state = json.load(f)
            age = time.time() - state.get("ts", 0) / 1000

            # Neow advice on GAME_START
            if state.get("event") == "GAME_START" and not self._opening_shown:
                self._opening_shown = True
                char_name = state.get("character", "")
                if char_name:
                    self._chat.say_opening(char_name)
                    neow_opts = state.get("event_options")
                    QTimer.singleShot(3000, lambda c=char_name, o=neow_opts:
                                      self._chat.say_neow_advice(c, event_options=o))

            # Keep GAME_START/ACT_START alive longer for Neow display
            is_start_event = state.get("event") in ("GAME_START", "ACT_START")
            if state.get("event") == "BATTLE_END" or (age > 60 and not is_start_event):
                state = None
        except Exception:
            state = None

        self._last_combat_state = state
        self._bubble.update_combat_state(state)

        # Intent change detection → chat bubble notification
        if state and state.get("event") not in ("GAME_START", "ACT_START", "BATTLE_END"):
            new_hash = _intent_hash(state)
            if new_hash and new_hash != self._last_intent_hash:
                self._last_intent_hash = new_hash
                self._notify_intent(state)
        elif not state:
            self._last_intent_hash = ""

    # ── 意图预测气泡 ────────────────────────────────────────
    def _notify_intent(self, state):
        monsters = state.get("monsters", [])
        if not monsters:
            return
        total_dmg = 0
        intent_parts = []
        INTENT_ZH = {
            "ATTACK": "攻击", "ATTACK_DEBUFF": "攻击+减益",
            "ATTACK_BUFF": "攻击+增益", "ATTACK_DEFEND": "攻击+防御",
            "DEFEND": "防御", "DEFEND_BUFF": "防御+增益",
            "BUFF": "增益", "DEBUFF": "减益", "STRONG_DEBUFF": "强减益",
            "MAGIC": "魔法", "SLEEP": "等待", "STUN": "眩晕",
            "ESCAPE": "逃跑", "UNKNOWN": "未知",
        }
        for m in monsters:
            name = m.get("name", "?")
            info = get_enemy_info(name)
            display = info.display if info else name
            dmg = m.get("dmg", 0)
            multi = m.get("multi", 1)
            intent = m.get("intent", "UNKNOWN")
            if dmg > 0:
                total_dmg += dmg * multi
                if multi > 1:
                    intent_parts.append(f"{display}→{dmg}×{multi}")
                else:
                    intent_parts.append(f"{display}→{dmg}")
            else:
                intent_z = INTENT_ZH.get(intent, intent)
                intent_parts.append(f"{display}→{intent_z}")
        if not intent_parts:
            return
        p = state.get("player", {})
        blk = p.get("block", 0)
        if total_dmg > 0:
            need = max(0, total_dmg - blk)
            if need > p.get("hp", 999) * 0.4:
                msg = f"⚠️ 即将受到{total_dmg}伤害！{' / '.join(intent_parts)}，注意防御！"
            elif need > 0:
                msg = f"🛡️ 还需{need}格挡，{' / '.join(intent_parts)}"
            else:
                msg = f"✅ 格挡充足！{' / '.join(intent_parts)}，全力输出！"
        else:
            msg = f"👀 {' / '.join(intent_parts)}，可趁机输出"
        self._chat.say(msg, category="intent", duration_ms=5000)

    def _on_pet_move(self):
        self._bubble.reposition()
        self._chat.reposition()

    def _toggle_pet(self):
        self._pet_visible = not self._pet_visible
        if self._pet_visible:
            if self._game_running:
                self._pet.show()
        else:
            self._pet.hide()
            self._bubble.hide_bubble()

    def _quit(self):
        self._watcher.stop()
        self._app.quit()


# ── 工具函数 ──────────────────────────────────────────────
def _intent_hash(state: dict) -> str:
    """Generate a hash of monster intents to detect turn changes."""
    if not state or "monsters" not in state:
        return ""
    parts = []
    for m in state.get("monsters", []):
        parts.append(f"{m.get('name','')}-{m.get('intent','')}-{m.get('dmg',0)}")
    return "|".join(parts)


def _act_label(data: dict) -> str:
    level = data.get("level_name", "")
    return LEVEL_NAMES.get(level, f"关卡{data.get('act_num', 1)}")


def _score_to_mood(score: int, alerts: list, hp_ratio: float = 1.0) -> str:
    """Enhanced mood with HP-linked states."""
    if hp_ratio < 0.15:
        return "critical"
    if alerts and score < 30:
        return "critical"
    if alerts:
        return "alert" if score < 40 else "worried"
    if hp_ratio > 0.8 and score >= 70:
        return "strong"
    if score >= 75:
        return "happy"
    if score >= 50:
        return "normal"
    if score >= 30:
        return "worried"
    return "alert"


def _generate_extreme_tip(character: str, data: dict, result) -> str | None:
    """Generate challenge build suggestions based on key cards/relics the player has.
    Only triggers when the player has the prerequisite cards or relics."""
    from core.config import get as cfg_get
    if not cfg_get("extreme_tips_enabled"):
        return None

    import random
    relics = parse_relics(data)
    deck = parse_deck(data)

    # ── Challenge builds triggered by specific card/relic combos ──
    tips = []

    # Ironclad combos
    if "Dead Branch" in relics and "Corruption" not in deck:
        tips.append("🔥 你有「死灵之书」！遇到「腐化」必拿——技能牌0费+消耗时随机生成新牌=无限循环！")
    if "Dead Branch" in relics and any("Corruption" in c for c in deck):
        tips.append("🔥 「死灵之书」+「腐化」已集齐！技能牌随便打，打完自动补牌，无敌组合！")
    if any("Searing Blow" in c for c in deck):
        tips.append("🔥 「灼热攻击」在手！每次休息升级它，升到+10以上单卡秒杀一切！极限流派！")
    if "Snecko Eye" in relics:
        tips.append("🔥 「蛇眼」在手——疯狂拿高费牌(3费以上)！它们可能变0费，越贵越赚！")
    if any("Limit Break" in c for c in deck) and any("Spot Weakness" in c for c in deck):
        tips.append("🔥 「突破极限」+「发现弱点」！力量无限翻倍流！多打精英试试爆发上限！")
    if "Barricade" in relics or any("Barricade" in c for c in deck):
        if any("Body Slam" in c for c in deck) or any("Entrench" in c for c in deck):
            tips.append("🔥 格挡叠层流！格挡不消失+翻倍+全身撞击=越打越硬！")

    # Silent combos
    if any("Catalyst" in c for c in deck) and any("Noxious Fumes" in c for c in deck):
        tips.append("🔥 「催化剂」+「毒雾」组合！升级催化剂翻3倍毒，Boss也是瞬间融化！")
    if any("Wraith Form" in c for c in deck) and any("After Image" in c for c in deck):
        tips.append("🔥 「幽灵形态」+「残影」！无实体+出牌就格挡=攻防一体，尝试0伤害通关！")
    if any("A Thousand Cuts" in c for c in deck) and any("Accuracy" in c for c in deck):
        tips.append("🔥 飞刀流核心已备！「精准」+「凌迟」+刀刃之舞=飞刀暴风雪！")

    # Defect combos
    if any("Creative AI" in c for c in deck):
        tips.append("🔥 「创意AI」在手！每回合自动获得能力牌，拖到后期越来越强！")
    if any("Electrodynamics" in c for c in deck) and any("Loop" in c for c in deck):
        tips.append("🔥 「电动力学」+「循环」！闪电球全体打击流！多引导闪电球试试！")
    if any("Echo Form" in c for c in deck):
        tips.append("🔥 有「回响形态」！每回合第一张牌打两遍，搭配高费大牌效果翻倍！")

    # Watcher combos
    if any("Blasphemy" in c for c in deck):
        tips.append("🔥 「渎神」= 下回合神性(伤害×3)！配合高伤攻击牌一回合秒Boss！风险极大！")
    if any("Rushdown" in c for c in deck) and any("Mental Fortress" in c for c in deck):
        tips.append("🔥 架势循环核心齐了！愤怒↔平静无限循环=无限抽牌+格挡！")
    if any("Devotion" in c for c in deck) and any("Wish" in c for c in deck):
        tips.append("🔥 「虔信」+「许愿」！真言流核心，每回合积攒能量最终爆发！")

    # Universal relic combos
    if "Ice Cream" in relics and "Chemical X" in relics:
        tips.append("🔥 「冰淇淋」+「化学X」！攒能量+X费牌额外+2费=毁灭级爆发！")
    if "Runic Pyramid" in relics:
        tips.append("🔥 「符文金字塔」留牌不弃！攒一手好牌爆发回合一波带走！注意手牌上限10张")
    if "Pandora's Box" in relics and result.floor <= 5:
        tips.append("🔥 「潘多拉之盒」开局变了基础牌！看看有没有神级组合，可能直接起飞！")

    return random.choice(tips) if tips else None


def main():
    _log("=== Companion starting ===")
    app = QApplication(sys.argv)
    app.setApplicationName("STS Companion")
    app.setQuitOnLastWindowClosed(False)
    comp = STSCompanion(app)
    _log(f"Init done, game_running={comp._game_running}, pet_visible={comp._pet_visible}")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
