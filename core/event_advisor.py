"""
Event room advisor - specific event identification + state-based advice.
Uses Java mod's event_name when available for targeted guidance.
"""
from core.archetypes import identify_archetype
from core.decoder import parse_deck, parse_relics
from core.scorer import CURSE_CARDS

# ── Specific event database ──────────────────────────────
# Key: Java class SimpleName from combat_state.json event_name
# Value: (中文名, advice_fn or str)
# Advice is context-dependent so we use functions where needed

_EVENT_DB: dict[str, tuple[str, str]] = {
    # ── Act 1 Events ──────────────────────────────────────
    "NeowEvent":         ("Neow的祝福",    "仔细选择，影响全局"),
    "BigFish":           ("大鱼",          "回血或获遗物都好，拿诅咒要慎重"),
    "GoldenIdolEvent":   ("金色神像",       "拿神像得诅咒+25HP伤害，血量高可考虑"),
    "LivingWall":        ("活体之墙",       "优先移除打击牌，升级核心牌也好"),
    "Mushrooms":         ("催眠蘑菇",       "打怪获遗物，或安全选+1最大HP"),
    "ShiningLight":      ("闪耀之光",       "升级2张牌，优质事件"),
    "GremlinMatchGame":  ("地精对对碰",     "翻牌配对游戏，配对成功获金币/升级/移除等奖励"),
    "Cleric":            ("牧师",           "35金回血35HP，50金移除1张牌，金够优先移除"),
    "GoldShrine":        ("金色圣坛",       "拿50金获诅咒——早期不推荐，有移除手段可考虑"),
    "ScrapOoze":         ("黏液坑",         "75金代价11HP，金币优先可拿"),
    "Bonfire":           ("篝火精灵",       "升级一张牌，好事件"),
    "DeadAdventurer":    ("死去的冒险者",    "搜索获遗物但可能触发战斗，强牌组可试"),
    "WomanInBlue":       ("蓝衣女人",       "买药水，20金/瓶，按需购买"),
    "NoteForYourself":   ("给自己的便条",    "可跨局存一张牌，一般跳过"),
    "TheLibrary":        ("图书馆",         "选牌机会，挑选适合流派的"),

    # ── Act 2 Events ──────────────────────────────────────
    "Colosseum":         ("斗兽场",         "连续2场战斗获稀有遗物，强牌组值得"),
    "Vampires":          ("吸血鬼",         "失去所有打击换Bite牌，打击多时很强"),
    "MaskedBandits":     ("面具强盗",       "交金币或战斗，有信心就打"),
    "ForgottenAltar":    ("被遗忘的祭坛",    "献血获遗物，血量充足可考虑"),
    "GhostlyEvent":      ("鬼魂议会",       "⚠️ 全牌组虚无化+获灵体牌，风险极大"),
    "TheNest":           ("鸟巢",           "回血并获金色遗物，通常值得"),
    "KnowingSkull":      ("知识头骨",       "花HP换金币/卡牌/遗物，血量充足可考虑"),
    "CursedTome":        ("被诅咒之书",      "获随机遗物但得诅咒，有移除手段可考虑"),
    "DrugDealer":        ("圆球+药水",      "药水交易，按需选择"),
    "Addict":            ("瘾君子",         "给牌获遗物，需评估牌组"),
    "BackToBasics":      ("返璞归真",       "升级所有打击和防御，打击多时有用"),
    "DesignerInSpire":   ("设计师",         "移除/改造/升级牌，优先移除"),

    # ── Act 3 Events ──────────────────────────────────────
    "MysteriousSphere":  ("神秘球体",       "战斗获稀有遗物，牌组强就打"),
    "SecretPortal":      ("秘密传送门",      "直达Boss跳过剩余楼层，确定强就走"),
    "MindBloom":         ("心灵绽放",       "三选一强力效果，根据牌组选最适合的"),
    "TheFalling":        ("坠落",           "必须移除一张牌，选最弱的"),
    "SensoryStone":      ("感知石",         "升级多张牌，价值极高的事件"),
    "TombOfLords":       ("领主之墓",       "打开棺材获遗物但战斗，选择要谨慎"),
    "WindingHalls":      ("蜿蜒回廊",       "回血/获金/获诅咒三选一"),
    "Moai":              ("摩艾石像",       "回满HP但-7最大HP，低血量时值得考虑"),

    # ── Universal Events ─────────────────────────────────
    "Duplicator":        ("复制机",         "复制一张牌，复制核心牌收益极大"),
    "FaceTrader":        ("面具商人",       "交换面具获随机遗物，看脸"),
    "Transmorgrifier":   ("改造机",         "改造一张牌为随机牌，不推荐核心牌"),
    "UpgradeShrine":     ("升级圣坛",       "升级一张牌"),
    "PurificationShrine":("净化圣坛",       "移除一张牌"),
    "WeMeetAgain":       ("又见面了",       "交出药水/金币/卡牌获遗物"),
    "WheelOfChange":     ("命运之轮",       "随机结果，赌博性质"),
    "GoldenWing":        ("金色之翼",       "飞跃楼层，跳过中间内容"),
    "AccursedBlacksmith":("被诅咒铁匠",     "升级牌但获诅咒，有移除手段可考虑"),
    "Lab":               ("实验室",         "获3瓶药水"),
    "NlothEvent":        ("恩洛斯的馈赠",    "交遗物换稀有遗物，看情况决定"),
}


def get_event_advice(character: str, save_data: dict,
                     event_name: str = "") -> dict:
    """
    Returns event advice dict.
    event_name: Java SimpleName from combat_state.json (optional).
    """
    deck = parse_deck(save_data)
    relics = parse_relics(save_data)
    gold = save_data.get("gold", 0) or 0
    hp = save_data.get("current_health", 0) or 0
    max_hp = save_data.get("max_health", 1) or 1
    floor = save_data.get("floor_num", 0)
    act = save_data.get("act_num", 1)
    hp_ratio = hp / max(max_hp, 1)
    deck_size = len(deck)
    curse_count = sum(1 for c in deck if any(curse in c for curse in CURSE_CARDS))

    tips = []
    specific_event = None
    specific_advice = ""

    # Try to identify specific event
    if event_name and event_name in _EVENT_DB:
        cn_name, advice = _EVENT_DB[event_name]
        specific_event = cn_name
        specific_advice = advice

    # State-based tips (concise, max 3)
    if hp_ratio >= 0.8:
        tips.append("💪 血量充足，可承受风险换取收益")
    elif hp_ratio >= 0.5:
        tips.append("🟡 血量中等，平衡风险和收益")
    elif hp_ratio < 0.35:
        tips.append("🔴 血量危险！选安全选项或回血")
    else:
        tips.append("🟠 血量偏低，优先回血选项")

    if deck_size > 25:
        tips.append("🃏 牌组臃肿，优先移除牌的选项")
    if curse_count > 0:
        tips.append(f"💀 有{curse_count}张诅咒，能移除就移除")

    # Priority
    if hp_ratio < 0.3:
        priority = "生存第一，拒绝风险"
    elif hp_ratio >= 0.8 and gold > 200:
        priority = "状态好，可冒险拿高收益"
    else:
        priority = "稳健选择，权衡收益"

    return {
        "tips": tips[:3],
        "priority": priority,
        "specific_event": specific_event,
        "specific_advice": specific_advice,
        "hp_ratio": hp_ratio,
        "gold": gold,
        "act": act,
    }


def get_event_chat_tip(character: str, save_data: dict,
                       event_name: str = "") -> str:
    """Generate a one-line event tip for the chat bubble."""
    # Try specific event first
    if event_name and event_name in _EVENT_DB:
        cn_name, advice = _EVENT_DB[event_name]
        return f"「{cn_name}」— {advice}"

    hp = save_data.get("current_health", 0) or 0
    max_hp = save_data.get("max_health", 1) or 1
    gold = save_data.get("gold", 0) or 0
    hp_ratio = hp / max(max_hp, 1)
    deck = parse_deck(save_data)
    deck_size = len(deck)

    if hp_ratio < 0.35:
        return "血量危险，选安全选项，能回血就回血"
    if hp_ratio > 0.8 and gold > 200:
        return "状态良好，可以冒险选高收益选项"
    if deck_size > 25:
        return "牌组偏多，优先选能移除牌的选项"
    if hp_ratio > 0.6:
        return "状态不错，根据流派需要选择"
    return "注意权衡风险和收益"
