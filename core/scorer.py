"""
牌组评分 + 胜率估算 + 主动提示生成。
评分满分 100，分四档：强(75+) / 中(50-74) / 弱(30-49) / 危险(<30)
"""
from dataclasses import dataclass
from core.archetypes import Archetype, identify_archetype, get_missing_cores
from core.decoder import parse_deck, parse_relics

CURSE_CARDS = {
    "Curse of the Bell", "CurseOfTheBell", "Clumsy", "Decay", "Doubt",
    "Injury", "Normality", "Pain", "Parasite", "Pride", "Regret",
    "Shame", "Writhe", "Necronomicurse",
}

BOSS_FLOORS = {16, 33, 50}
ACT_FLOORS  = {17, 34}   # 进入新章节

# Powerful relic combos
RELIC_COMBOS = [
    ({"Dead Branch", "Corruption"}, "死灵之书+腐化：技能牌消耗后随机生成新牌，无限循环！", "IRONCLAD"),
    ({"Snecko Eye"}, "蛇眼在手：优先拿高费牌(2+费)，随机费用让高费牌更划算", None),
    ({"Ice Cream"}, "冰淇淋：可以攒能量到爆发回合一波打出", None),
    ({"Runic Pyramid"}, "符文金字塔：不弃牌，攒一手好牌一回合打出！注意牌组别太大", None),
    ({"Velvet Choker"}, "天鹅绒项圈：每回合限6张牌，避免拿太多0费牌", None),
    ({"Kunai", "Shuriken"}, "苦无+手里剑：攻击3次同时+1敏捷+1力量，飞刀流神器", "THE_SILENT"),
    ({"Inserter", "Defragment"}, "插件器+碎片化：充能球位多+专注高，充能球伤害翻倍", "DEFECT"),
    ({"Violet Lotus"}, "紫莲花：退出平静时+1能量，观者循环切换架势核心", "WATCHER"),
    ({"Pandora's Box"}, "潘多拉之盒：所有基础牌变随机牌，开局后检查牌组重新规划流派", None),
    ({"Nuclear Battery", "Inserter"}, "核电池+插件器：首回合充能球+每2回合+1球位，机器人起飞", "DEFECT"),
]


@dataclass
class ScoreResult:
    score: int               # 0-100
    grade: str               # S/A/B/C/D
    archetype_name: str      # 主流派名
    archetype_icon: str      # emoji
    tips: list[str]          # 建议列表
    alerts: list[str]        # 主动弹出的警告
    floor: int
    act: int
    hp: int
    max_hp: int
    deck_size: int
    curse_count: int
    win_rate: int            # 估算胜率 0-100
    gold: int = 0            # 当前金币


_WEAK_CARDS = {
    "IRONCLAD":   ["Strike_R", "Defend_R", "Anger", "Clash"],
    "THE_SILENT": ["Strike_G", "Defend_G", "Neutralize"],
    "DEFECT":     ["Strike_B", "Defend_B", "Zap"],
    "WATCHER":    ["Strike_P", "Defend_P", "Evaluate"],
}

def _find_weak_cards(character: str, deck: list[str]) -> list[str]:
    """Find removable weak cards in the deck."""
    from core.card_advisor import _cn_name
    weak = _WEAK_CARDS.get(character, [])
    found = []
    for w in weak:
        if any(w in c for c in deck):
            found.append(_cn_name(w))
    return found


def _grade(score: int) -> str:
    if score >= 85: return "S"
    if score >= 70: return "A"
    if score >= 50: return "B"
    if score >= 30: return "C"
    return "D"


def evaluate(character: str, save_data: dict) -> ScoreResult:
    deck    = parse_deck(save_data)
    relics  = parse_relics(save_data)
    floor   = save_data.get("floor_num", 0)
    act     = save_data.get("act_num", 1)
    hp      = save_data.get("current_health", 0) or 0
    max_hp  = save_data.get("max_health", 1)     or 1
    gold    = save_data.get("gold", 0)            or 0

    curse_count = sum(1 for c in deck if any(curse in c for curse in CURSE_CARDS))
    deck_size   = len(deck)

    # ── 流派识别 ──────────────────────────────────────────
    arch_matches = identify_archetype(character, deck)
    if arch_matches:
        top_arch, core_cnt, syn_cnt = arch_matches[0]
        arch_name = top_arch.name
        arch_icon = top_arch.icon
        core_total = len(top_arch.core)
        syn_total  = max(len(top_arch.synergy), 1)
        core_ratio = core_cnt / max(core_total, 1)
        syn_ratio  = syn_cnt  / syn_total
    else:
        top_arch   = None
        arch_name  = "无明确流派"
        arch_icon  = "❓"
        core_ratio = 0
        syn_ratio  = 0
        core_cnt   = 0

    # ── 评分计算 ──────────────────────────────────────────
    score = 50   # 基准分

    # 流派完整度 (+35)
    score += int(core_ratio * 25)
    score += int(syn_ratio  * 10)

    # 多流派冲突惩罚（前两名都有核心牌，且流派不兼容）
    if len(arch_matches) >= 2 and arch_matches[1][1] >= 1:
        score -= 8

    # 牌组大小惩罚（大于20张扣分）
    if deck_size > 25:
        score -= (deck_size - 25) * 2
    elif deck_size > 20:
        score -= (deck_size - 20) * 1

    # 诅咒惩罚
    score -= curse_count * 6

    # 遗物加分（流派强力遗物）
    if top_arch:
        relic_bonus = sum(1 for r in top_arch.relics if any(r in rel for rel in relics))
        score += relic_bonus * 4

    # 血量比例
    hp_ratio = hp / max_hp
    if hp_ratio < 0.3:
        score -= 10
    elif hp_ratio > 0.7:
        score += 5

    # 章节进度加分（活得越久越厉害）
    score += min(floor // 5, 8)

    score = max(0, min(100, score))

    # ── 胜率估算 ──────────────────────────────────────────
    # 基于评分做非线性映射：弱牌也有基础胜率，强牌不封顶100
    win_rate = int(20 + score * 0.65)
    win_rate = max(5, min(95, win_rate))

    # ── 建议生成 ──────────────────────────────────────────
    tips: list[str] = []
    alerts: list[str] = []

    if top_arch:
        missing = get_missing_cores(top_arch, deck)
        if missing:
            sources = []
            if act <= 1:
                sources.append("精英战掉落")
            if gold >= 100:
                sources.append("商店购买")
            sources.append("战斗奖励")
            tip = f"核心牌缺失：{', '.join(missing)}，可通过{'、'.join(sources)}获取"
            tips.append(tip)
            if len(missing) >= 2:
                alerts.append(
                    f"⚠️ {arch_name}核心牌严重不足（缺{len(missing)}张），"
                    f"下次选牌优先拿：{missing[0]}")

        if syn_ratio < 0.3 and core_cnt >= 1:
            tips.append(f"协同牌较少，考虑拿取：{', '.join(top_arch.synergy[:3])}")

        tips.append(f"当前流派：{arch_icon} {arch_name} — {top_arch.tip}")

    if len(arch_matches) >= 2 and arch_matches[1][1] >= 1:
        a0, a1 = arch_matches[0][0], arch_matches[1][0]
        stronger = a0.name if arch_matches[0][1] >= arch_matches[1][1] else a1.name
        tips.append(f"牌组兼有{a0.name}和{a1.name}，建议专注{stronger}方向")

    if deck_size > 22:
        weak_cards = _find_weak_cards(character, deck)
        if weak_cards:
            tips.append(f"牌组{deck_size}张偏多，建议移除：{', '.join(weak_cards[:2])}")
        else:
            tips.append(f"牌组{deck_size}张偏多，考虑在营地/商店移除弱牌")

    if curse_count > 0:
        removal = "商店净化(50金)" if gold >= 50 else "营地事件"
        tips.append(f"含{curse_count}张诅咒牌，优先通过{removal}移除")
        if curse_count >= 2:
            alerts.append(f"🩸 {curse_count}张诅咒严重拖累牌组，每张-6分，"
                          f"建议立即前往商店净化")

    if hp_ratio < 0.35:
        if hp <= 10:
            alerts.append(f"💀 血量极低（{hp}/{max_hp}），一场战斗可能致命！"
                          f"优先找营地/回血事件")
        else:
            alerts.append(f"❤️ 血量偏低（{hp}/{max_hp}），"
                          f"下个营地建议休息回复{int(max_hp*0.3)}点HP")

    if score < 40:
        if top_arch:
            alerts.append(f"😨 牌组较弱，建议专注{arch_name}方向，"
                          f"优先获取核心牌提升强度")
        else:
            alerts.append("😨 牌组缺少方向，下次选牌时关注有协同效果的牌，"
                          "避免拿散牌")

    # Boss 预警（含具体Boss信息）
    next_boss = next((b for b in sorted(BOSS_FLOORS) if b > floor), None)
    if next_boss and next_boss - floor <= 3:
        from core.combat_advisor import get_enemy_info
        boss_list = save_data.get("boss_list", [])
        boss_name = boss_list[0] if boss_list else None
        boss_info = get_enemy_info(boss_name) if boss_name else None
        boss_display = boss_info.display if boss_info else "Boss"

        if hp_ratio < 0.6:
            advice = f"⚔️ {boss_display}在第{next_boss}层，血量不足，先回血！"
            if boss_info:
                advice += f"\n💡 {boss_info.strategy}"
            alerts.append(advice)
        else:
            tip = f"距{boss_display}还有{next_boss - floor}层"
            if boss_info and boss_info.priority_hint:
                tip += f"，准备好{boss_info.priority_hint}"
            tips.append(tip)

    # 开局建议（前3层）
    if floor <= 3 and act == 1:
        tips.append("开局阶段，优先拿强力攻击牌快速击杀敌人减少受伤")

    # 遗物组合建议
    relic_set = set(relics)
    for combo_relics, combo_tip, combo_char in RELIC_COMBOS:
        if combo_char and combo_char != character:
            continue
        if combo_relics.issubset(relic_set):
            tips.append(f"🔮 {combo_tip}")
        elif len(combo_relics) == 2:
            have = combo_relics & relic_set
            missing = combo_relics - relic_set
            if len(have) == 1:
                have_name = next(iter(have))
                miss_name = next(iter(missing))
                if any(miss_name in c for c in deck):
                    tips.append(f"🔮 你有{have_name}，如果再拿到{miss_name}可以组成强力combo")

    if not tips:
        tips.append("牌组运转良好，继续保持！")

    return ScoreResult(
        score=score,
        grade=_grade(score),
        archetype_name=arch_name,
        archetype_icon=arch_icon,
        tips=tips,
        alerts=alerts,
        floor=floor,
        act=act,
        hp=hp,
        max_hp=max_hp,
        deck_size=deck_size,
        curse_count=curse_count,
        win_rate=win_rate,
        gold=gold,
    )
