"""
Card advice with relic synergy and explanations.
Recommends pickup / remove / upgrade based on deck, relics, and archetype.
"""
from dataclasses import dataclass, field
from core.archetypes import identify_archetype, ARCHETYPES

# ── Relic-Card synergy database ──────────────────────────
# {relic_id: [(card_id, reason), ...]}
RELIC_CARD_SYNERGY: dict[str, list[tuple[str, str]]] = {
    # Ironclad
    "Dead Branch":      [("Corruption", "腐化+死灵之书=无限生成牌，神级组合"),
                         ("Feel No Pain", "消耗触发格挡+摸牌")],
    "Snecko Eye":       [("Demon Form", "高费牌被降费后超值"),
                         ("Impervious", "5费牌可能变0费"),
                         ("Bludgeon", "高费大伤害牌最受益")],
    "Vajra":            [("Heavy Blade", "力量翻倍效果更强"),
                         ("Limit Break", "初始力量翻倍基数更高")],
    "Paper Phrog":      [("Body Slam", "易伤让格挡流伤害翻倍"),
                         ("Heavy Blade", "易伤+力量=爆炸伤害")],
    "Champion Belt":    [("Whirlwind", "每段攻击都上弱化"),
                         ("Sword Boomerang", "多段触发弱化")],
    "Bag of Marbles":   [("Heavy Blade", "开局易伤+力量=首回合秒杀")],
    "Charon's Ashes":   [("Corruption", "消耗技能牌触发全体伤害")],
    # Silent
    "Shuriken":         [("Blade Dance", "一次出牌触发3次攻击计数"),
                         ("Cloak and Dagger", "飞刀计数利器")],
    "Kunai":            [("Blade Dance", "3次攻击=+1敏捷"),
                         ("Infinite Blades", "每回合自动攻击计数")],
    "Snecko Skull":     [("Noxious Fumes", "每回合额外+1毒"),
                         ("Deadly Poison", "毒量提升")],
    "Tough Bandages":   [("Tactician", "弃牌=格挡+能量"),
                         ("Calculated Gamble", "全弃=大量格挡")],
    "Tingsha":          [("Acrobatics", "弃牌=额外伤害"),
                         ("Calculated Gamble", "弃越多伤害越高")],
    "Ninja Scroll":     [("Accuracy", "3把飞刀开局，配合精准伤害翻倍")],
    # Defect
    "Inserter":         [("Defragment", "更多充能槽+集中=球更强"),
                         ("Capacitor", "扩展充能搭配自动插入")],
    "Nuclear Battery":  [("Multicast", "暗能球开局直接释放"),
                         ("Darkness", "暗能球叠加后释放")],
    "Runic Capacitor":  [("Glacier", "更多球槽=更多冰球=更多格挡"),
                         ("Defragment", "球越多集中收益越大")],
    "Data Disk":        [("Defragment", "+1集中让所有球更强"),
                         ("Loop", "首球效果增强")],
    # Watcher
    "Violet Lotus":     [("Eruption", "退出平静+能量=爆发"),
                         ("Tranquility", "切换姿态获得能量")],
    "Duality":          [("Eruption", "攻击+敏捷"),
                         ("Ragnarok", "多段攻击多次触发")],
    # Universal
    "Calipers":         [("Barricade", "格挡保留组合，防御无敌"),
                         ("Glacier", "冰球格挡不流失")],
    "Chemical X":       [("Whirlwind", "X费牌+3能量=毁灭"),
                         ("Multicast", "X费释放更多次")],
    "Ice Cream":        [("Whirlwind", "攒能量一次打光"),
                         ("Multicast", "攒能量释放更多球")],
}

# ── Remove priority per character ────────────────────────
REMOVE_PRIORITY: dict[str, list[str]] = {
    "IRONCLAD":   ["Strike_R", "Defend_R", "Anger", "Clash", "Headbutt",
                   "Pommel Strike", "Twin Strike", "Warcry"],
    "THE_SILENT": ["Strike_G", "Defend_G", "Neutralize", "Survivor",
                   "Acrobatics", "Dagger Spray", "Dagger Throw"],
    "DEFECT":     ["Strike_B", "Defend_B", "Zap", "Dualcast",
                   "Hologram", "Stack"],
    "WATCHER":    ["Strike_P", "Defend_P", "Eruption", "Vigilance",
                   "Evaluate", "Prostrate"],
}

# ── Upgrade priority per character ───────────────────────
UPGRADE_PRIORITY: dict[str, list[str]] = {
    "IRONCLAD":   ["Barricade", "Impervious", "Body Slam", "Limit Break",
                   "Entrench", "Corruption", "Demon Form", "Feel No Pain",
                   "Dark Embrace", "Whirlwind", "Berserk"],
    "THE_SILENT": ["Catalyst", "Noxious Fumes", "Accuracy", "Infinite Blades",
                   "A Thousand Cuts", "Nightmare", "Adrenaline", "Burst"],
    "DEFECT":     ["Defragment", "Glacier", "Electrodynamics", "Loop",
                   "Biased Cognition", "Echo Form", "Consume", "Claw"],
    "WATCHER":    ["Devotion", "Indignation", "Scrawl", "Establishment",
                   "Mental Fortress", "Wish", "Vault"],
}

# ── Survival / transition cards ──────────────────────────
# Cards that help survive while building toward a combo.
# Recommended when core cards are missing to prevent dying.
SURVIVAL_CARDS: dict[str, list[tuple[str, str]]] = {
    "IRONCLAD": [
        ("Shrug It Off", "基础格挡+抽牌，各流派都强"),
        ("Battle Trance", "0费抽3张，加速找核心牌"),
        ("True Grit", "格挡+消耗手牌弱牌"),
        ("Offering", "抽3张+2能量，关键回合爆发"),
        ("Iron Wave", "攻防兼备过渡牌"),
    ],
    "THE_SILENT": [
        ("Footwork", "+敏捷，大幅提升所有格挡效果"),
        ("Leg Sweep", "格挡+弱化，攻防兼备"),
        ("Well-Laid Plans", "保留关键牌，控制手牌"),
        ("Adrenaline", "0费抽2+1能量，万能过渡"),
        ("Dodge and Roll", "格挡+下回合也格挡"),
    ],
    "DEFECT": [
        ("Glacier", "格挡+2冰球，攻防兼备"),
        ("Coolheaded", "格挡+抽牌，冰球通用"),
        ("Self Repair", "每回合回血续航"),
        ("Hologram", "回收弃牌堆关键牌"),
        ("Charge Battery", "格挡+下回合能量"),
    ],
    "WATCHER": [
        ("Vigilance", "进入平静+格挡，架势循环基础"),
        ("Talk to the Hand", "攻击生成格挡，攻防一体"),
        ("Tantrum", "多段攻击+进入愤怒"),
        ("Inner Peace", "平静中抽牌，保持手牌质量"),
        ("Empty Fist", "进入愤怒的廉价攻击"),
    ],
}


@dataclass
class CardAdvice:
    remove:   list[tuple[str, str]]  # [(card_cn, reason), ...]
    pickup:   list[tuple[str, str]]  # [(card_cn, reason), ...]
    upgrade:  list[tuple[str, str]]  # [(card_cn, reason), ...]
    summary:  str
    relic_synergies: list[str] = field(default_factory=list)  # relic-card tips


def get_card_advice(character: str, deck: list[str],
                    floor: int = 0, relics: list[str] | None = None,
                    upgraded_ids: dict[str, int] | None = None) -> CardAdvice:
    arch_matches = identify_archetype(character, deck)
    top_arch = arch_matches[0][0] if arch_matches else None
    relics = relics or []

    # ── Relic-card synergy ────────────────────────────────
    relic_tips = []
    relic_pickups = []
    for relic in relics:
        if relic in RELIC_CARD_SYNERGY:
            for card_id, reason in RELIC_CARD_SYNERGY[relic]:
                has_card = any(card_id in c for c in deck)
                if not has_card:
                    relic_pickups.append((card_id, f"配合{_cn_relic(relic)}：{reason}"))
                else:
                    relic_tips.append(f"✨ {_cn_relic(relic)}+{_cn_name(card_id)}：{reason}")

    # ── Remove advice ────────────────────────────────────
    base_removes = REMOVE_PRIORITY.get(character, [])
    removes = []
    for card in base_removes:
        count = sum(1 for c in deck if c == card or c == card + "+1")
        if count > 0:
            cn = _cn_name(card)
            if "Strike" in card:
                removes.append((cn, "基础攻击牌，移除提升牌组质量"))
            elif "Defend" in card:
                removes.append((cn, "基础防御牌，流派成型后可移除"))
            else:
                removes.append((cn, "替代性强，精简牌组"))

    # ── Pickup advice ────────────────────────────────────
    pickups = []
    core_pickup_count = 0
    if top_arch:
        for card in top_arch.core:
            if not any(card in c for c in deck):
                pickups.append((_cn_name(card),
                    f"{top_arch.name}核心牌，获取后显著提升流派强度"))
                core_pickup_count += 1

    # Add relic-synergy pickups (highest priority)
    for card_id, reason in relic_pickups[:3]:
        cn = _cn_name(card_id)
        if not any(p[0] == cn for p in pickups):
            pickups.insert(0, (cn, reason))

    # ── Survival / transition card advice ────────────────
    # When core cards are missing, recommend survival cards after core recs
    survival_tips = []
    if top_arch:
        missing_core = [c for c in top_arch.core if not any(c in d for d in deck)]
        if missing_core:
            survival = SURVIVAL_CARDS.get(character, [])
            for card_id, reason in survival:
                if not any(card_id in c for c in deck):
                    survival_tips.append((_cn_name(card_id), f"过渡牌：{reason}"))
                    if len(survival_tips) >= 2:
                        break
    elif not pickups:
        survival = SURVIVAL_CARDS.get(character, [])
        for card_id, reason in survival[:2]:
            if not any(card_id in c for c in deck):
                survival_tips.append((_cn_name(card_id), f"通用好牌：{reason}"))

    # Insert survival cards right after core recs, before synergy
    insert_pos = len(pickups)  # after core + relic synergy
    for i, s in enumerate(survival_tips):
        if not any(p[0] == s[0] for p in pickups):
            pickups.insert(insert_pos + i, s)

    # Then add synergy cards
    if top_arch:
        for card in top_arch.synergy[:5]:
            if not any(card in c for c in deck):
                cn = _cn_name(card)
                if not any(p[0] == cn for p in pickups):
                    pickups.append((cn,
                        f"与{top_arch.name}协同，补强牌组"))

    # ── Upgrade advice ───────────────────────────────────
    prio = UPGRADE_PRIORITY.get(character, [])
    upgrades = []
    upgrade_counts = upgraded_ids or {}
    for card in prio:
        # Count total copies in deck vs already-upgraded copies
        total_in_deck = sum(1 for c in deck if c == card)
        already_up = upgrade_counts.get(card, 0)
        un_upgraded = total_in_deck - already_up
        if un_upgraded > 0:
            reason = _upgrade_reason(card)
            if total_in_deck > 1 and already_up > 0:
                reason = f"你有{total_in_deck}张，{already_up}张已升级，还有{un_upgraded}张待升级！" + reason
            upgrades.append((_cn_name(card), reason))
        if len(upgrades) >= 4:
            break

    # ── Summary ──────────────────────────────────────────
    if top_arch:
        core_have = sum(1 for c in top_arch.core if any(c in d for d in deck))
        core_total = len(top_arch.core)
        if core_have == core_total:
            summary = f"{top_arch.icon}{top_arch.name} 核心完整，专注协同与升级"
        elif core_have == 0:
            summary = f"尚未建立 {top_arch.name}，优先拿取核心牌"
        else:
            summary = f"{top_arch.name} 核心 {core_have}/{core_total}，继续补全"
        # Alternative archetype hint
        if len(arch_matches) > 1:
            alt = arch_matches[1][0]
            alt_core = sum(1 for c in alt.core if any(c in d for d in deck))
            if alt_core > 0:
                summary += f"（也可转{alt.icon}{alt.name}）"
        # Missing core warning
        if top_arch.warn_missing:
            missing_warns = [_cn_name(c) for c in top_arch.warn_missing
                             if not any(c in d for d in deck)]
            if missing_warns:
                summary += f"\n⚠️ 缺少关键牌「{'、'.join(missing_warns)}」，注意拿过渡牌保命"
    else:
        summary = "牌组方向不明，建议专注一个流派，先拿通用好牌过渡"

    return CardAdvice(
        remove=removes[:4],
        pickup=pickups[:6],
        upgrade=upgrades[:4],
        summary=summary,
        relic_synergies=relic_tips[:3],
    )


# ── Card name translation (official in-game Chinese) ─────
_CN: dict[str, str] = {
    # Ironclad
    "Strike_R": "打击", "Defend_R": "防御",
    "Barricade": "壁垒", "Body Slam": "全身撞击",
    "Entrench": "巩固", "Impervious": "岿然不动",
    "Limit Break": "突破极限", "Inflame": "燃烧",
    "Demon Form": "恶魔形态", "Feel No Pain": "无惧疼痛",
    "Dark Embrace": "黑暗之拥", "Corruption": "腐化",
    "Berserk": "狂暴", "Brutality": "残暴",
    "Whirlwind": "旋风斩", "Offering": "祭品",
    "Second Wind": "重振精神", "Pommel Strike": "剑柄打击",
    "Twin Strike": "双重打击", "Anger": "愤怒",
    "Headbutt": "头槌", "Warcry": "战吼",
    "Clash": "交锋", "Shrug It Off": "耸肩无视",
    "Heavy Blade": "重刃", "Spot Weakness": "发现弱点",
    "Sword Boomerang": "回旋镖", "Flex": "弯曲",
    "Immolate": "献祭", "Juggernaut": "主宰",
    "Sentinel": "哨兵", "Battle Trance": "战斗恍惚",
    "Exhume": "掘墓", "Bludgeon": "痛击",
    "Iron Wave": "铁浪", "Armaments": "武装",
    "True Grit": "刚毅", "Rage": "怒火",
    "Wild Strike": "野蛮打击", "Bloodletting": "放血",
    "Combust": "燃烧弹", "Rupture": "破裂",
    "Searing Blow": "灼热攻击", "Feed": "吞噬",
    # Silent
    "Strike_G": "打击", "Defend_G": "防御",
    "Catalyst": "催化剂", "Noxious Fumes": "毒雾",
    "Blade Dance": "刀刃之舞", "Accuracy": "精准",
    "Infinite Blades": "无限刀刃", "A Thousand Cuts": "凌迟",
    "Neutralize": "中和", "Survivor": "生存者",
    "Acrobatics": "杂技", "Dagger Spray": "匕首雨",
    "Dagger Throw": "投掷匕首",
    "Nightmare": "噩梦", "Adrenaline": "肾上腺素", "Burst": "爆发",
    "Cloak and Dagger": "暗器", "After Image": "残影",
    "Finisher": "终结", "Predator": "捕食者",
    "Well-Laid Plans": "精心布局", "Deadly Poison": "致命毒药",
    "Bouncing Flask": "弹跳药瓶", "Envenom": "淬毒",
    "Corpse Explosion": "尸爆", "Crippling Cloud": "致残烟雾",
    "Bane": "祸根", "Tactician": "战术家",
    "Reflex": "反射神经", "Calculated Gamble": "赌一把",
    "Sneaky Strike": "偷袭", "Expertise": "专长",
    "Wraith Form": "幽灵形态", "Footwork": "身法",
    "Blur": "模糊", "Setup": "布局",
    "Flying Knee": "飞膝",
    "Leg Sweep": "扫堂腿", "Dodge and Roll": "翻滚回避",
    # Defect
    "Strike_B": "打击", "Defend_B": "防御",
    "Defragment": "碎片整理", "Glacier": "冰川",
    "Electrodynamics": "电动力学", "Loop": "循环",
    "Biased Cognition": "偏差认知", "Echo Form": "回响形态",
    "Zap": "电击", "Dualcast": "双重释放",
    "Hologram": "全息影像", "Stack": "堆栈",
    "Consume": "耗尽", "Claw": "利爪",
    "Ball Lightning": "球状闪电", "Static Discharge": "静电释放",
    "Amplify": "放大", "Thunderstrike": "雷击",
    "Capacitor": "电容器", "Multicast": "多重释放",
    "Coolheaded": "冷静", "Cold Snap": "急冻",
    "Creative AI": "创意AI", "Darkness": "暗能量",
    "Reboot": "重启", "Self Repair": "自修复",
    "Charge Battery": "充电电池",
    # Watcher
    "Strike_P": "打击", "Defend_P": "防御",
    "Devotion": "虔信", "Indignation": "义愤填膺",
    "Establishment": "确立基础", "Mental Fortress": "心灵堡垒",
    "Wish": "许愿", "Vault": "腾跃",
    "Eruption": "暴怒", "Vigilance": "警惕",
    "Evaluate": "评估", "Prostrate": "五体投地",
    "Scrawl": "潦草急就", "Tranquility": "宁静",
    "Reach Heaven": "触及天堂", "Through Violence": "以暴制暴",
    "Rushdown": "猛攻", "Sands of Time": "时间之沙",
    "Brilliance": "辉煌", "Alpha": "阿尔法",
    "Ragnarok": "诸神黄昏", "Inner Peace": "内心平静",
    "Like Water": "如水", "Worship": "崇拜",
    "Judgement": "审判", "Talk to the Hand": "以手交谈",
    "Empty Fist": "空拳",
    # Universal
    "Apotheosis": "神化", "Pandora's Box": "潘多拉之盒",
}

_RELIC_CN: dict[str, str] = {
    "Dead Branch": "死灵之书", "Snecko Eye": "蛇眼",
    "Vajra": "金刚杵", "Paper Phrog": "纸蛙",
    "Champion Belt": "冠军腰带", "Bag of Marbles": "弹珠袋",
    "Charon's Ashes": "冥河灰烬", "Shuriken": "手里剑",
    "Kunai": "苦无", "Snecko Skull": "蛇眼头骨",
    "Tough Bandages": "硬绷带", "Tingsha": "叮铛",
    "Ninja Scroll": "忍术卷轴", "Inserter": "插入器",
    "Nuclear Battery": "核能电池", "Runic Capacitor": "符文电容",
    "Data Disk": "数据盘", "Violet Lotus": "紫莲花",
    "Duality": "二元性", "Calipers": "卡尺",
    "Chemical X": "化学X", "Ice Cream": "冰淇淋",
    "Membership Card": "会员卡", "Old Coin": "旧硬币",
    "Singing Bowl": "歌唱碗", "Anchor": "船锚",
    "Horn Cleat": "系缆柱", "Lantern": "灯笼",
    "Pen Nib": "钢笔尖", "Courier": "信使",
    "Lee's Waffle": "华夫饼", "Mango": "芒果",
}


def _cn_name(card_id: str) -> str:
    return _CN.get(card_id, card_id)


def _cn_relic(relic_id: str) -> str:
    return _RELIC_CN.get(relic_id, relic_id)


def _upgrade_reason(card_id: str) -> str:
    reasons = {
        "Barricade": "升级后减少1费，更容易打出",
        "Body Slam": "升级后0费，配合格挡无限输出",
        "Impervious": "升级后40格挡，保命神技",
        "Limit Break": "升级后力量不再减半，无限翻倍",
        "Entrench": "升级后格挡翻倍效率更高",
        "Corruption": "升级后减费，更早打出",
        "Demon Form": "升级后每回合+3力量",
        "Feel No Pain": "升级后消耗给4格挡",
        "Dark Embrace": "升级后消耗给2张牌",
        "Whirlwind": "升级后每段+3伤害",
        "Berserk": "升级后减少1易伤层",
        "Catalyst": "升级后毒量三倍而非两倍",
        "Noxious Fumes": "升级后每回合+3毒",
        "Accuracy": "升级后飞刀+6伤害",
        "Defragment": "升级后+2集中",
        "Glacier": "升级后+2格挡",
        "Electrodynamics": "升级后多1个闪电球",
        "Echo Form": "升级后减费，核心牌必升",
        "Devotion": "升级后+4神圣",
        "Mental Fortress": "升级后+6格挡",
    }
    return reasons.get(card_id, "升级后效果显著提升")


def _is_universal_good(card_id: str) -> bool:
    return card_id in {
        "Apotheosis", "Pandora's Box", "True Grit",
        "Shrug It Off", "Armaments",
    }
