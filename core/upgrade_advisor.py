"""
Upgrade advisor — recommend which card to upgrade at rest sites.
Based on community consensus upgrade priorities from STS wiki and competitive play.
"""

# Card upgrade priority database
# Key: card ID (internal English), Value: (priority 0-100, Chinese name, upgrade reason)
# Higher priority = upgrade sooner
_UPGRADE_DB: dict[str, tuple[int, str, str]] = {
    # ── IRONCLAD ──────────────────────────────────────
    "Bash":             (95, "痛击",     "易伤 2→3 回合"),
    "Feed":             (92, "吞噬",     "回复 3→4 HP，滚雪球"),
    "Demon Form":       (90, "恶魔化",   "费用 3→2"),
    "Limit Break":      (88, "突破极限", "不再消耗"),
    "Offering":         (85, "祭品",     "抽 3→5 张牌"),
    "Corruption":       (83, "堕落",     "费用 3→2"),
    "Impervious":       (82, "坚不可摧", "格挡 30→40"),
    "Shrug It Off":     (80, "耸肩回避", "格挡 8→11，核心防御"),
    "Flame Barrier":    (78, "烈焰屏障", "反伤 4→7"),
    "Carnage":          (75, "残忍击",   "伤害 20→28"),
    "Reaper":           (78, "收割者",   "伤害 4→5 全体吸血"),
    "Whirlwind":        (72, "旋风斩",   "每次 +5 伤害"),
    "Body Slam":        (68, "躯体猛撞", "费用 1→0"),
    "Metallicize":      (70, "金属化",   "回合末 3→4 格挡"),
    "Barricade":        (75, "壁垒",     "费用 3→2"),
    "Bloodletting":     (65, "放血",     "能量 1→2"),
    "Pommel Strike":    (60, "拳击",     "伤害 9→10，抽 1→2"),
    "True Grit":        (58, "坚韧不拔", "格挡 7→9"),
    "Uppercut":         (65, "上勾拳",   "弱化/易伤 1→2 回合"),

    # ── THE SILENT ────────────────────────────────────
    "Footwork":         (95, "足部工作", "敏捷 +2→+3"),
    "Noxious Fumes":    (92, "毒雾",     "每回合 2→3 毒"),
    "Catalyst":         (90, "催化剂",   "毒翻倍→翻3倍"),
    "Burst":            (88, "弹幕",     "1→2 张技能牌翻倍"),
    "Wraith Form":      (88, "幽灵形态", "无实体 2→3 回合"),
    "After Image":      (85, "残影",     "每出牌 +1 格挡不变但值得"),
    "Malaise":          (82, "虚弱",     "消耗全部能量施加更多弱化"),
    "Well-Laid Plans":  (80, "深谋远虑", "保留 1→2 张牌"),
    "Adrenaline":       (78, "肾上腺素", "抽 2→3 张"),
    "Neutralize":       (75, "中和",     "伤害 3→4，弱化 1→2"),
    "Deadly Poison":    (72, "致命毒药", "毒 5→7"),
    "Blade Dance":      (70, "剑刃舞",   "3→4 把匕首"),
    "Leg Sweep":        (68, "横扫腿",   "格挡+弱化都增加"),
    "Accuracy":         (65, "精准",     "匕首 +4→+6 伤害"),
    "Backstab":         (60, "背刺",     "伤害 11→15"),
    "Dash":             (62, "冲刺",     "伤害+格挡 10→13"),
    "Piercing Wail":    (65, "刺耳尖叫", "减伤 6→8"),
    "Phantasmal Killer":(72, "幻影杀手", "费用 1→0"),

    # ── DEFECT ────────────────────────────────────────
    "Defragment":       (95, "碎片整理", "集中 +1→+2"),
    "Glacier":          (90, "冰川",     "格挡 7→10"),
    "Echo Form":        (88, "回响形态", "费用 3→2"),
    "Electrodynamics":  (88, "电动力学", "额外引导闪电球"),
    "Capacitor":        (82, "电容器",   "充能球位 +2→+3"),
    "Coolheaded":       (80, "冷静",     "格挡 6→9"),
    "Zap":              (78, "电击",     "费用 1→0"),
    "Doom and Gloom":   (75, "末日",     "伤害 10→14"),
    "Claw":             (68, "利爪",     "伤害 3→5"),
    "Biased Cognition": (82, "偏执认知", "集中 +4→+5"),
    "Consume":          (72, "吞噬",     "集中 +2→+3"),
    "Genetic Algorithm":(70, "遗传算法", "格挡逐回合增长更多"),
    "Fusion":           (65, "融合",     "费用 2→1"),
    "Hyperbeam":        (70, "超光速粒子", "伤害 26→34"),
    "Buffer":           (78, "缓冲",     "费用 2→1? 仍1次防死"),
    "Seek":             (75, "搜索",     "搜 1→2 张牌"),

    # ── WATCHER ───────────────────────────────────────
    "Eruption":         (98, "爆发",     "费用 2→1，全游戏最佳升级"),
    "Rushdown":         (92, "急躁",     "抽 1→2 张"),
    "Mental Fortress":  (90, "精神堡垒", "换架势 +4→+6 格挡"),
    "Talk to the Hand": (88, "切磋",     "+2→+3 格挡每次攻击"),
    "Wallop":           (82, "重锤",     "伤害 9→12"),
    "Tantrum":          (80, "暴怒",     "3→4 次攻击"),
    "Worship":          (75, "崇拜",     "真言 5→7"),
    "Blasphemy":        (72, "渎神",     "变为保留"),
    "Vigilance":        (70, "警戒",     "格挡 8→12"),
    "Conclude":         (68, "终结",     "伤害 12→16"),
    "Lesson Learned":   (78, "前车之鉴", "伤害 6→10"),
    "Ragnarok":         (75, "诸神黄昏", "5→6 次攻击"),
    "Halt":             (60, "停驻",     "格挡 3→4 +格挡追加"),
    "Flurry of Blows":  (55, "乱拳",     "伤害 4→6"),
    "Empty Fist":       (58, "空拳",     "伤害 9→14"),
    "Tranquility":      (65, "宁静",     "费用 1→0"),

    # ── BASIC CARDS (low priority) ────────────────────
    "Strike_R":         (15, "打击",     "伤害 6→9"),
    "Strike_G":         (15, "打击",     "伤害 6→9"),
    "Strike_B":         (15, "打击",     "伤害 6→9"),
    "Strike_P":         (15, "打击",     "伤害 6→9"),
    "Defend_R":         (20, "防御",     "格挡 5→8"),
    "Defend_G":         (20, "防御",     "格挡 5→8"),
    "Defend_B":         (20, "防御",     "格挡 5→8"),
    "Defend_P":         (20, "防御",     "格挡 5→8"),
    "AscendersBane":    (0,  "登塔者之灾", "诅咒牌，无法升级"),
}

# Heuristic priority for unknown cards by type
_TYPE_BASE = {
    "POWER":  55,
    "SKILL":  40,
    "ATTACK": 35,
    "STATUS": 0,
    "CURSE":  0,
}


def get_upgrade_recommendations(
    deck: list[dict],
    character: str = "",
    top_n: int = 3,
) -> list[dict]:
    """Analyze deck and return top upgrade recommendations.

    Args:
        deck: list of card dicts with keys: id, name, upgraded, type, rarity
        character: character class name (for context)
        top_n: how many recommendations to return

    Returns:
        list of {id, name, priority, reason} dicts, sorted by priority desc
    """
    candidates = []
    for card in deck:
        if card.get("upgraded") or card.get("times_upgraded", 0) > 0:
            continue
        card_id = card.get("id", "")
        card_name = card.get("name", card_id)
        card_type = card.get("type", "")

        if card_type in ("STATUS", "CURSE"):
            continue

        if card_id in _UPGRADE_DB:
            pri, cn_name, reason = _UPGRADE_DB[card_id]
            candidates.append({
                "id": card_id,
                "name": cn_name or card_name,
                "priority": pri,
                "reason": reason,
            })
        else:
            # Heuristic for unknown cards
            base = _TYPE_BASE.get(card_type, 30)
            rarity = card.get("rarity", "")
            if rarity == "RARE":
                base += 15
            elif rarity == "UNCOMMON":
                base += 5
            candidates.append({
                "id": card_id,
                "name": card_name,
                "priority": base,
                "reason": "值得考虑",
            })

    # Deduplicate (same card_id, keep highest priority)
    seen = {}
    for c in candidates:
        cid = c["id"]
        if cid not in seen or c["priority"] > seen[cid]["priority"]:
            seen[cid] = c
    candidates = sorted(seen.values(), key=lambda x: x["priority"], reverse=True)
    return candidates[:top_n]


def get_rest_advice(
    deck: list[dict],
    hp: int,
    max_hp: int,
    character: str = "",
) -> str:
    """Generate rest site advice: rest vs upgrade + which card to upgrade.

    Returns a concise advice string for chat bubble display.
    """
    hp_ratio = hp / max(max_hp, 1)
    recs = get_upgrade_recommendations(deck, character, top_n=2)

    if hp_ratio < 0.35:
        advice = f"血量只有{hp}/{max_hp}（{hp_ratio:.0%}），强烈建议休息回血！"
        if recs:
            advice += f"\n如果执意升级，推荐升级「{recs[0]['name']}」（{recs[0]['reason']}）"
        return advice

    if hp_ratio < 0.55:
        advice = f"血量{hp}/{max_hp}，休息回血更安全"
        if recs and recs[0]["priority"] >= 85:
            advice = f"血量{hp}/{max_hp}不多，但「{recs[0]['name']}」升级收益极大（{recs[0]['reason']}），可以考虑冒险升级"
        return advice

    # HP is decent — recommend upgrade
    if not recs:
        return "血量充足，但没有特别需要升级的牌，可以休息"

    top = recs[0]
    advice = f"血量充足，建议升级「{top['name']}」（{top['reason']}）"
    if len(recs) > 1:
        advice += f"，其次「{recs[1]['name']}」"
    return advice
