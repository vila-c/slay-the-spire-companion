"""
Chat bubble v2 - small popup above the pet for contextual tips.
- Auto-shows on room/event changes
- Auto-hides after a few seconds
- Phase2: 大量对话模板、事件建议、开局/幕间/Boss台词
"""
import random
from PyQt6.QtWidgets import QWidget, QLabel, QVBoxLayout, QApplication
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont

from core.config import get as cfg_get

# STS palette
BG_BUBBLE  = "#2a1a08"
BORDER     = "#c9a84c"
TEXT_COLOR  = "#f0e6d3"
GOLD       = "#c9a84c"

MAX_HISTORY = 50


class ChatBubble(QWidget):
    def __init__(self, pet_widget):
        super().__init__()
        self._pet = pet_widget
        self._history: list[dict] = []
        self._auto_hide_timer = QTimer()
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self._fade_out)
        self._setup_window()
        self._build_ui()
        self._fade = QPropertyAnimation(self, b"windowOpacity")
        self._fade.setDuration(200)
        self._fade.setEasingCurve(QEasingCurve.Type.OutCubic)

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint      |
            Qt.WindowType.WindowStaysOnTopHint     |
            Qt.WindowType.Tool                     |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setMaximumWidth(280)
        self.setWindowOpacity(0)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel()
        self._label.setWordWrap(True)
        self._label.setTextFormat(Qt.TextFormat.RichText)
        self._label.setStyleSheet(f"""
            QLabel {{
                background: {BG_BUBBLE};
                color: {TEXT_COLOR};
                border: 2px solid {BORDER};
                border-radius: 12px;
                padding: 10px 14px;
                font-size: 12px;
            }}
        """)
        layout.addWidget(self._label)

    # ── Public API ───────────────────────────────────────
    def say(self, text: str, category: str = "tip",
            duration_ms: int = 5000, record: bool = True):
        if not cfg_get("chat_bubble_enabled"):
            if record:
                self._add_history(text, category)
            return

        name = cfg_get("player_name") or "主人"
        display = text.replace("{name}", name)
        self._label.setText(display)
        self._position_above_pet()

        if record:
            self._add_history(display, category)

        self.show()
        self._fade.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(1.0)
        self._fade.start()

        self._auto_hide_timer.start(duration_ms)

    def say_room(self, room_type: str, context: dict):
        msg = _generate_room_message(room_type, context)
        if msg:
            cat = "extreme" if context.get("extreme") else "room"
            # Shorter duration for combat rooms, longer for non-combat
            duration = 4000 if room_type in ("monster", "elite") else 10000
            self.say(msg, category=cat, duration_ms=duration)

    def say_opening(self, character: str):
        """Opening game greeting with starting relic info."""
        msg = random.choice(_OPENING_GREETS).format(
            name="{name}", char=_char_cn(character))
        relic = _STARTING_RELICS.get(character)
        if relic:
            msg += f"\n🔮 初始遗物「{relic[0]}」：{relic[1]}"
        self.say(msg, category="opening", duration_ms=8000)

    def say_neow_advice(self, character: str,
                        event_options: list[dict] | None = None):
        """Neow bonus selection advice.
        If event_options is provided (from Java mod), gives advice based on
        actual available options instead of generic tips.
        """
        if event_options:
            # Score actual options and find the best
            scored = []
            for opt in event_options:
                text = opt.get("text", "")
                disabled = opt.get("disabled", False)
                if disabled or not text:
                    continue
                advice, score = _score_neow_option(text)
                scored.append((text, advice, score))

            if scored:
                scored.sort(key=lambda x: x[2], reverse=True)
                best_text, best_advice, _ = scored[0]
                # Truncate option text for bubble display
                short = best_text[:20] + "…" if len(best_text) > 20 else best_text
                msg = f"{{name}}，Neow 的祝福！\n⭐ 推荐「{short}」\n💡 {best_advice}"
                # Warn about bad options
                for text, advice, score in scored:
                    if score < 0 and "⚠" in advice:
                        short_bad = text[:15] + "…" if len(text) > 15 else text
                        msg += f"\n⚠️ 「{short_bad}」{advice}"
                        break
                self.say(msg, category="neow", duration_ms=12000)
                return

        # Fallback: generic advice when options aren't available
        advice = _NEOW_ADVICE.get(character, _NEOW_ADVICE_GENERAL)
        msg = random.choice(_NEOW_GREETS).format(
            name="{name}", advice=random.choice(advice))
        self.say(msg, category="neow", duration_ms=10000)

    def say_act_transition(self, act: int):
        """Act transition message."""
        if act in _ACT_LINES:
            msg = random.choice(_ACT_LINES[act]).format(name="{name}")
            self.say(msg, category="act", duration_ms=7000)

    def say_relic(self, relic_id: str, character: str, deck: list[str]):
        """Relic pickup notification with synergy advice."""
        info = _RELIC_ADVICE.get(relic_id)
        if not info:
            return
        cn_name, advice, synergy_cards = info
        msg = f"✨ 获得遗物「{cn_name}」！\n{advice}"
        # Check if player has synergy cards
        if synergy_cards:
            has = [c for c in synergy_cards if any(c in d for d in deck)]
            if has:
                from core.card_advisor import _cn_name
                names = "、".join(_cn_name(c) for c in has[:2])
                msg += f"\n🔗 配合你的「{names}」效果更强！"
        self.say(msg, category="relic", duration_ms=6000)

    def say_idle(self, score: int, hp_ratio: float):
        """Random idle chatter based on state."""
        pool = _IDLE_GOOD if score >= 60 else (_IDLE_MID if score >= 35 else _IDLE_BAD)
        msg = random.choice(pool).format(name="{name}")
        self.say(msg, category="idle", duration_ms=5000)

    def get_history(self) -> list[dict]:
        return list(self._history)

    def clear_history(self):
        self._history.clear()

    def reposition(self):
        if self.isVisible() and self.windowOpacity() > 0.05:
            self._position_above_pet()

    # ── Internal ─────────────────────────────────────────
    def _add_history(self, text: str, category: str):
        import time
        self._history.append({
            "text": text, "category": category,
            "ts": time.time(),
        })
        if len(self._history) > MAX_HISTORY:
            self._history = self._history[-MAX_HISTORY:]

    def _position_above_pet(self):
        self.adjustSize()
        pet_rect = self._pet.geometry()
        x = pet_rect.center().x() - self.width() // 2
        y = pet_rect.top() - self.height() - 8

        screen = QApplication.primaryScreen().geometry()
        if y < 0:
            y = pet_rect.bottom() + 8
        x = max(0, min(x, screen.width() - self.width()))
        y = max(0, min(y, screen.height() - self.height()))
        self.move(x, y)

    def _fade_out(self):
        self._fade.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.finished.connect(self._on_hidden)
        self._fade.start()

    def _on_hidden(self):
        try:
            self._fade.finished.disconnect(self._on_hidden)
        except Exception:
            pass
        if self.windowOpacity() < 0.05:
            self.hide()

    def mousePressEvent(self, event):
        self._auto_hide_timer.stop()
        self._fade_out()
        event.accept()


def _char_cn(char: str) -> str:
    return {"IRONCLAD": "铁甲", "THE_SILENT": "寂静",
            "DEFECT": "机器人", "WATCHER": "观者"}.get(char, char)


_STARTING_RELICS = {
    "IRONCLAD":    ("燃烧之血", "战斗后回复6点HP"),
    "THE_SILENT":  ("蛇戒", "首回合额外抽2张牌"),
    "DEFECT":      ("裂核", "回合开始时若无充能球则引导1个闪电球"),
    "WATCHER":     ("圣水", "每回合开始加1张奇迹牌到手牌"),
}


# ── Message templates ────────────────────────────────────

# --- Battle ---
_BATTLE_GREETS = [
    "⚔️ 注意！{enemy}出现了！\n💡 {strategy}\n点击宠物查看详细打法~",
    "⚔️ {name}，前方{enemy}！\n💡 {strategy}",
    "⚔️ 小心！{enemy}！\n💡 {strategy}\n需要详细打法点击宠物~",
]

_ELITE_GREETS = [
    "💀 精英怪「{enemy}」！小心！\n💡 {strategy}\n点击宠物查看应对方案",
    "💀 {name}，精英战！「{enemy}」很强\n💡 {strategy}",
]

# --- Boss ---
_BOSS_WARNINGS = [
    "👑 Boss「{enemy}」来了！{advice}\n点我查看详情",
    "👑 {name}，决战！「{enemy}」！{advice}",
]

# --- Shop ---
_SHOP_GREETS = [
    "{name}，到商店了！你有{gold}金币，{advice}",
    "{name}，商店来了，{advice}",
    "到商店了~{gold}金在手，{advice}",
    "{name}，逛逛商店，{advice}",
]

# --- Rest ---
_REST_GREETS = [
    "{name}，到营地了，{advice}",
    "{name}，休息一下吧，{advice}",
    "营地到了，{name}，{advice}",
    "停下脚步喘口气，{name}，{advice}",
]

# --- Event (with advice) ---
_EVENT_GREETS = [
    "🎲 遇到事件了！{advice}",
    "{name}，事件房间！{advice}",
    "🎲 {advice}",
]

# --- Extreme tips ---
_EXTREME_TIPS = [
    "{name}，我有一个大胆的想法... {tip}",
    "{name}，要不要来点刺激的？{tip}",
    "嘿{name}，冒险一下？{tip}",
    "{name}，赌一把！{tip}",
]

# --- Treasure ---
_TREASURE_GREETS = [
    "{name}，宝箱！打开看看有什么好东西~",
    "💰 发现宝箱了！{name}，期待遗物吧！",
    "{name}，宝箱房间！希望是个好遗物！",
]

# --- Opening game ---
_OPENING_GREETS = [
    "{name}，新的冒险开始了！{char}出发！",
    "欢迎回来{name}！{char}准备好了吗？",
    "{name}，{char}的旅途开始，我会一路陪伴你的！",
    "出发吧{name}！让我们带{char}征服尖塔！",
    "{name}，又一次挑战尖塔！我会提供最好的建议！",
]

# --- Act transitions ---
_ACT_LINES = {
    2: [
        "{name}，第二幕开始了！城市比想象的更危险~",
        "进入城市了！{name}，注意精英怪变强了！",
        "{name}，第二幕！敌人更强但奖励也更好，加油！",
    ],
    3: [
        "{name}，第三幕！最终挑战来了！",
        "深处...{name}，这里的怪物很可怕，保持警惕！",
        "{name}，最后一幕了！保持冷静，相信你的牌组！",
    ],
    4: [
        "{name}，终幕！最终Boss等着你！",
        "这是最后的战斗了！{name}，全力以赴！",
    ],
}

# --- Idle chatter ---
_IDLE_GOOD = [
    "{name}，牌组状态不错哦~",
    "继续保持{name}！这副牌组很有潜力！",
    "{name}，你的选择很棒，继续这个方向！",
    "干得好{name}，保持这个节奏！",
]
_IDLE_MID = [
    "{name}，牌组还需要加强，注意拿牌方向~",
    "{name}，加油，多拿核心牌提升强度！",
    "还行{name}，但可以更好，注意流派搭配！",
]
_IDLE_BAD = [
    "{name}，牌组需要改善...注意拿牌策略！",
    "{name}，情况有点艰难，但别放弃！",
    "坚持住{name}，找机会补强牌组！",
]

# --- Post-combat ---
_POST_COMBAT_WIN = [
    "漂亮{name}！战斗胜利！",
    "{name}，赢了！好好选牌~",
    "干得好{name}！看看有什么好牌可以拿！",
]

_POST_COMBAT_HURT = [
    "{name}，赢了但受伤不少，注意回血！",
    "虽然赢了...但{name}血量下降了，小心！",
]

# --- Neow bonus ---
_NEOW_GREETS = [
    "{name}，Neow 的祝福！{advice}",
    "{name}，开局选择很关键！{advice}",
    "仔细选择 Neow 的赠礼，{name}！{advice}",
    "{name}，这是影响全局的第一个选择！{advice}",
]

_NEOW_ADVICE_GENERAL = [
    "升级攻击牌通常比升级防御牌好，升级后的打击能更快清怪",
    "移除一张打击比拿一个随机遗物更稳定",
    "如果有「选一张稀有牌」选项，优先考虑",
    "100金币很诱人，但好的遗物/卡牌对开局影响更大",
    "「变换一张牌」风险较高，除非你知道可能变出什么",
    "⚠️「交换初始遗物→随机Boss遗物」风险极大！初始遗物非常重要，除非你对Boss遗物池很熟，否则不建议换",
]

_NEOW_ADVICE = {
    "IRONCLAD": [
        "铁甲开局如果能升级「痛击」非常强，易伤从2回合变3回合",
        "移除一张打击让牌组更精简，铁甲靠质量不靠数量",
        "⚠️ 交换初始遗物要三思！「燃烧之血」每场战斗后回6血，是铁甲续航核心",
        "铁甲选择升级牌时优先升级「痛击」，3回合易伤非常强力",
    ],
    "THE_SILENT": [
        "寂静升级「中和」很稳——0费4伤害+2弱化",
        "寂静开局精简牌组最重要，移除打击优先",
        "⚠️ 交换初始遗物要三思！「蛇戒」首回合+2抽牌，对开局极重要",
        "如果有随机稀有牌选项，寂静的稀有牌整体质量高",
    ],
    "DEFECT": [
        "机器人升级「电击」可以引导闪电球而非覆盖已有充能球",
        "机器人开局最需要充能球位，相关遗物优先",
        "⚠️ 交换初始遗物要三思！「裂核」自动引导闪电球，是早期输出来源",
        "机器人升级「双重施法」可以0费使用，配合闪电球很强",
    ],
    "WATCHER": [
        "观者升级「爆发」从2费变1费，切换架势更灵活",
        "观者最强开局之一：升级「爆发」+ 早期拿「急躁」",
        "⚠️ 交换初始遗物要三思！「圣水」每回合给1张「奇迹」牌(0费+1能量)，非常强",
        "观者移除打击比其他角色更重要，平静/愤怒循环不需要基础攻击",
    ],
}


def _generate_room_message(room_type: str, ctx: dict) -> str | None:
    if ctx.get("extreme"):
        tip = ctx.get("extreme_tip", "")
        if tip:
            return random.choice(_EXTREME_TIPS).format(
                name="{name}", tip=tip)
        return None

    if room_type == "monster":
        enemy = ctx.get("enemy_display", "未知敌人")
        strategy = ctx.get("strategy", "小心应对")
        return random.choice(_BATTLE_GREETS).format(
            name="{name}", enemy=enemy, strategy=strategy)

    elif room_type == "elite":
        enemy = ctx.get("enemy_display", "未知精英")
        strategy = ctx.get("strategy", "全力以赴")
        return random.choice(_ELITE_GREETS).format(
            name="{name}", enemy=enemy, strategy=strategy)

    elif room_type == "boss":
        enemy = ctx.get("enemy_display", "Boss")
        advice = ctx.get("advice", "全力以赴！")
        return random.choice(_BOSS_WARNINGS).format(
            name="{name}", enemy=enemy, advice=advice)

    elif room_type == "shop":
        gold = ctx.get("gold", 0)
        advice = ctx.get("shop_advice", "看看有什么好东西")
        return random.choice(_SHOP_GREETS).format(
            name="{name}", gold=gold, advice=advice)

    elif room_type == "rest":
        advice = ctx.get("rest_advice", "休息还是升级牌？")
        return random.choice(_REST_GREETS).format(
            name="{name}", advice=advice)

    elif room_type == "event":
        advice = ctx.get("event_advice", "注意选项，权衡风险和收益！")
        return random.choice(_EVENT_GREETS).format(
            name="{name}", advice=advice)

    elif room_type == "treasure":
        return random.choice(_TREASURE_GREETS).format(name="{name}")

    return None


# ── Relic advice database ────────────────────────────────
# Key: relic internal ID
# Value: (中文名, 简明建议, [synergy_card_ids])
_RELIC_ADVICE: dict[str, tuple[str, str, list[str]]] = {
    # ── Boss Relics ──────────────────────────────────────
    "Snecko Eye":       ("蛇眼",       "所有牌费用随机0-3！多拿高费牌",          []),
    "Runic Pyramid":    ("符文金字塔",   "回合结束不弃牌！攒好牌一次爆发",         []),
    "Pandora's Box":    ("潘多拉之盒",   "所有基础牌变随机牌！看看组合",           []),
    "Sozu":             ("酒壶",         "+1能量但不能获得药水",                   []),
    "Empty Cage":       ("空笼子",       "移除2张牌，精简牌组",                    []),
    "Astrolabe":        ("星盘",         "改造3张牌，可能出好牌",                  []),
    "Calling Bell":     ("召唤铃",       "获3个遗物但也得1张诅咒",                 []),
    "Cursed Key":       ("诅咒钥匙",     "+1能量但开宝箱得诅咒",                   []),
    "Ectoplasm":        ("灵质",         "+1能量但不能获得金币",                   []),
    "Philosopher's Stone":("贤者之石",   "+1能量但敌人+1力量",                     []),
    "Busted Crown":     ("破碎王冠",     "+1能量但选牌只有2选1",                   []),
    "Coffee Dripper":   ("咖啡壶",       "+1能量但不能在营地休息",                 []),
    "Fusion Hammer":    ("熔合之锤",     "+1能量但不能在营地升级",                 []),
    "Mark of Pain":     ("痛苦印记",     "+1能量但抽2张伤口到手",                  []),
    "Runic Dome":       ("符文穹顶",     "+1能量但看不到敌人意图",                 []),
    "Velvet Choker":    ("天鹅绒项圈",   "+1能量但每回合最多出6张牌",              []),
    "Tiny House":       ("小房子",       "什么都给一点的万金油遗物",               []),
    "Sacred Bark":      ("圣树皮",       "药水效果翻倍！",                         []),
    "Black Star":       ("黑星",         "精英掉落2个遗物！多打精英",              []),

    # ── Key Relics with Synergy ──────────────────────────
    "Dead Branch":      ("死灵之书",     "消耗牌时随机生成新牌！配腐化=无限",      ["Corruption", "Feel No Pain"]),
    "Ice Cream":        ("冰淇淋",       "能量不清零！攒能量爆发",                 ["Whirlwind", "Multicast"]),
    "Chemical X":       ("化学X",        "X费牌+2费！X牌收益翻倍",                ["Whirlwind", "Multicast", "Malaise"]),
    "Vajra":            ("金刚杵",       "+1力量，攻击流更强",                      ["Heavy Blade", "Limit Break"]),
    "Shuriken":         ("手里剑",       "一回合打3张攻击牌+1力量",                ["Blade Dance", "Sword Boomerang"]),
    "Kunai":            ("苦无",         "一回合打3张攻击牌+1敏捷",                ["Blade Dance", "Cloak and Dagger"]),
    "Calipers":         ("卡尺",         "格挡保留(超出15部分)！防御流神器",        ["Barricade", "Glacier"]),
    "Tough Bandages":   ("硬绷带",       "弃牌时获3格挡",                          ["Tactician", "Calculated Gamble"]),
    "Tingsha":          ("叮铛",         "弃牌时对随机敌人造3伤害",                ["Acrobatics", "Calculated Gamble"]),
    "Bag of Marbles":   ("弹珠袋",       "战斗开始敌人全体易伤1层",                []),
    "Anchor":           ("船锚",         "战斗开始获10格挡",                       []),
    "Lantern":          ("灯笼",         "战斗开始+1能量",                         []),
    "Pen Nib":          ("钢笔尖",       "每10次攻击牌伤害翻倍",                   []),
    "Ornamental Fan":   ("折扇",         "一回合打3张攻击牌获4格挡",               []),
    "Letter Opener":    ("裁纸刀",       "一回合打3张技能牌对全体敌人造5伤害",     []),

    # ── Character-specific ───────────────────────────────
    "Black Blood":      ("黑血",         "战后回12HP（替换燃烧之血）",             []),
    "Ring of the Snake": ("蛇戒",        "首回合+2抽牌",                           []),
    "Ring of the Serpent":("蛇之环",      "首回合+2抽牌（替换蛇戒）",              []),
    "FrozenCore":       ("冰封核心",     "回合结束无充能球时引导冰球",              ["Defragment", "Capacitor"]),
    "HolyWater":        ("圣水",         "每回合加1张奇迹牌(0费+1能量)",           ["Eruption", "Rushdown"]),
    "Violet Lotus":     ("紫莲花",       "退出平静+1能量！架势循环核心",           ["Eruption", "Tranquility"]),
}


def _score_neow_option(text: str) -> tuple[str, int]:
    """Score a Neow option text and return (advice, score).
    Higher score = better option. Mirrors bubble.py logic."""
    t = text.lower()
    # Relic swap (highest risk)
    if any(k in t for k in ("替换", "交换", "boss遗物", "初始遗物",
                             "starting relic", "boss relic")):
        return ("会失去初始遗物！风险极大", -10)
    # Transform (random result)
    if "变换" in t or "变化" in t or "转化" in t:
        return ("随机变换，结果不可控", -5)
    # Remove card
    if "移除" in t:
        return ("精简牌组提升抽牌质量", 90)
    # Upgrade specific card
    if "升级" in t and "随机" not in t:
        return ("升级核心牌效果翻倍", 85)
    # Upgrade random card
    if "升级" in t and "随机" in t:
        return ("随机升级，运气成分大", 50)
    # Choose a rare card
    if "稀有" in t and ("选" in t or "获得" in t):
        return ("稀有牌质量高，推荐", 80)
    # Random rare card
    if "稀有" in t:
        return ("随机稀有牌，多数不错", 65)
    # Colorless card
    if "无色" in t:
        return ("无色牌有好选择", 55)
    # Random relic
    if "遗物" in t:
        return ("遗物对全局有影响", 60)
    # Gold
    if any(k in t for k in ("金币", "250金", "100金", "金")):
        return ("金币不如牌/遗物直接", 35)
    # Max HP gain
    if ("生命" in t or "hp" in t) and any(k in t for k in ("获得", "增加", "提升", "最大")):
        return ("额外血量提升容错", 45)
    # HP loss
    if ("生命" in t or "hp" in t) and any(k in t for k in ("失去", "损失", "减少")):
        return ("注意HP代价", 20)
    # Potions
    if "药水" in t:
        return ("药水仅一次性，收益最低", 15)
    # Card choice
    if "选择" in t and "牌" in t:
        return ("可以选牌，看具体选项", 55)
    return ("", 0)

