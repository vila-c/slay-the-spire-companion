"""
四角色流派定义 + 流派识别逻辑。
关键牌分为：核心牌(core) 和 协同牌(synergy)。
核心牌是流派的标志性牌，协同牌是锦上添花的牌。
"""
from dataclasses import dataclass, field

@dataclass
class Archetype:
    name: str           # 显示名称（中文）
    icon: str           # emoji 图标
    core: list[str]     # 核心牌（有这些牌才算这个流派）
    synergy: list[str]  # 协同牌（加分项）
    relics: list[str]   # 强力配合遗物
    tip: str            # 流派简介
    warn_missing: list[str] = field(default_factory=list)  # 缺失时主动提醒的牌


ARCHETYPES: dict[str, list[Archetype]] = {
    "IRONCLAD": [
        Archetype(
            name="力量流",
            icon="💪",
            core=["Limit Break", "Inflame", "Spot Weakness"],
            synergy=["Heavy Blade", "Sword Boomerang", "Whirlwind", "Flex", "Demon Form",
                     "Immolate", "Juggernaut", "Second Wind", "Offering", "Berserk"],
            relics=["Paper Phrog", "Vajra", "Champion Belt", "Bag of Marbles"],
            tip="通过叠加力量层数，让大伤害牌打出爆炸伤害",
            warn_missing=["Limit Break"],
        ),
        Archetype(
            name="格挡流",
            icon="🛡️",
            core=["Barricade", "Body Slam"],
            synergy=["Entrench", "Impervious", "Shrug It Off", "Second Wind",
                     "Feel No Pain", "Juggernaut", "Iron Wave"],
            relics=["Calipers", "Orichalcum", "Girya", "Anchor"],
            tip="保留格挡叠加，用 Body Slam 打出巨额伤害",
            warn_missing=["Barricade", "Body Slam"],
        ),
        Archetype(
            name="消耗流",
            icon="🔥",
            core=["Feel No Pain", "Dark Embrace"],
            synergy=["Corruption", "Dead Branch", "Offering", "Sentinel",
                     "Battle Trance", "Immolate", "Headbutt", "Exhume"],
            relics=["Dead Branch", "Charon's Ashes", "Rupture"],
            tip="通过消耗牌触发 Feel No Pain 摸牌/格挡，搭配 Dark Embrace 摸牌",
            warn_missing=["Feel No Pain"],
        ),
        Archetype(
            name="出血暴怒流",
            icon="😡",
            core=["Berserk", "Brutality"],
            synergy=["Rupture", "Combust", "Rage", "Wild Strike", "Bloodletting",
                     "Headbutt", "Offering", "Immolate"],
            relics=["Rupture", "Burning Blood", "Centennial Puzzle"],
            tip="通过自我伤害触发特效，叠加爆发伤害",
            warn_missing=[],
        ),
    ],

    "THE_SILENT": [
        Archetype(
            name="飞刀流",
            icon="🗡️",
            core=["Blade Dance", "Accuracy"],
            synergy=["Cloak and Dagger", "Infinite Blades", "After Image",
                     "Finisher", "Predator", "Unceasing Top", "Well-Laid Plans"],
            relics=["Kunai", "Shuriken", "Ninja Scroll"],
            tip="大量生成飞刀并用 Accuracy 提升伤害，飞刀数量就是输出",
            warn_missing=["Accuracy"],
        ),
        Archetype(
            name="毒流",
            icon="☠️",
            core=["Noxious Fumes", "Catalyst"],
            synergy=["Deadly Poison", "Bouncing Flask", "Envenom", "Corpse Explosion",
                     "Crippling Cloud", "Swift Strike", "Bane"],
            relics=["Snecko Skull", "Toxic Egg"],
            tip="叠加大量毒层，用 Catalyst 翻倍后等敌人死亡",
            warn_missing=["Catalyst"],
        ),
        Archetype(
            name="弃牌流",
            icon="🃏",
            core=["Tactician", "Reflex"],
            synergy=["Acrobatics", "Skullsplitter", "Calculated Gamble",
                     "Sneaky Strike", "Expertise", "Nightmare"],
            relics=["Tingsha", "Tough Bandages"],
            tip="通过弃牌触发特效获取额外能量/摸牌",
            warn_missing=[],
        ),
        Archetype(
            name="无限循环",
            icon="♾️",
            core=["Unceasing Top"],
            synergy=["Setup", "Flying Knee", "Infinite Blades", "After Image",
                     "Blur", "Footwork", "Wraith Form"],
            relics=["Velvet Choker"],
            tip="利用 Unceasing Top 的特殊机制打出无限连",
            warn_missing=["Unceasing Top"],
        ),
    ],

    "DEFECT": [
        Archetype(
            name="闪电流",
            icon="⚡",
            core=["Electrodynamics", "Ball Lightning"],
            synergy=["Static Discharge", "Amplify", "Thunderstrike", "Consume",
                     "Capacitor", "Defragment", "Echo Form", "Multicast"],
            relics=["Inserter", "Nuclear Battery", "Runic Capacitor"],
            tip="召唤大量闪电球，用 Electrodynamics 让所有球打全体",
            warn_missing=["Electrodynamics"],
        ),
        Archetype(
            name="寒冰流",
            icon="❄️",
            core=["Glacier", "Blizzard"],
            synergy=["Coolheaded", "Chill", "Frozen Eye", "White Noise",
                     "Cold Snap", "Defragment", "Echo Form"],
            relics=["Cryo-stone", "Frozen Core"],
            tip="叠加大量冰球获取格挡，用 Blizzard 打出等比伤害",
            warn_missing=["Blizzard"],
        ),
        Archetype(
            name="爪爪流",
            icon="🐾",
            core=["Claw"],
            synergy=["Cold Snap", "Compile Driver", "Stack", "Overclock",
                     "Recycle", "Darkness", "All for One"],
            relics=["Chemical X", "Data Disk"],
            tip="通过打出多张 Claw 使其永久强化，爆发输出",
            warn_missing=["Claw"],
        ),
        Archetype(
            name="黑暗/创意流",
            icon="🌑",
            core=["Creative AI", "Darkness"],
            synergy=["Amplify", "Multicast", "Defragment", "Echo Form",
                     "Reboot", "Melter", "Self Repair"],
            relics=["Maw Bank", "Snecko Eye", "Runic Dome"],
            tip="用 Creative AI 每回合获得随机法术，Darkness 叠层爆发",
            warn_missing=[],
        ),
    ],

    "WATCHER": [
        Archetype(
            name="冲突循环流",
            icon="☯️",
            core=["Eruption", "Vigilance"],
            synergy=["Prostrate", "Tranquility", "Reach Heaven", "Through Violence",
                     "Rushdown", "Establishment", "Sands of Time", "Brilliance"],
            relics=["Violet Lotus", "Yang"],
            tip="在狂乱/平静之间切换，每次切换触发 Rushdown 摸牌并获得额外能量",
            warn_missing=["Eruption"],
        ),
        Archetype(
            name="凝视预言流",
            icon="👁️",
            core=["Foresight", "Evaluate"],
            synergy=["Halt", "Pray", "Sanctity", "Perseverance", "Brilliance",
                     "Just Lucky", "Sash Whip", "Weave"],
            relics=["Frozen Eye", "Pure Water"],
            tip="通过 Scry 精准控制手牌，Evaluate 叠加神圣层获得大量格挡",
            warn_missing=[],
        ),
        Archetype(
            name="保留神意流",
            icon="✨",
            core=["Alpha", "Ragnarok"],
            synergy=["Brilliance", "Judgement", "Inner Peace", "Like Water",
                     "Mental Fortress", "Establishment", "Worship"],
            relics=["Mark of Pain", "Violet Lotus", "Cloak Clasp"],
            tip="进入神意状态打出 Ragnarok 造成超高伤害，Alpha 循环续航",
            warn_missing=["Alpha"],
        ),
    ],
}


def identify_archetype(character: str, deck: list[str]) -> list[tuple[Archetype, int, int]]:
    """
    识别牌组流派。
    返回列表：[(archetype, core_count, synergy_count), ...]，按核心牌数量降序排列。
    只返回至少有1张核心牌的流派。
    """
    deck_set = set(deck)
    results = []

    for arch in ARCHETYPES.get(character, []):
        core_count = sum(1 for c in arch.core if any(c in d for d in deck_set))
        synergy_count = sum(1 for c in arch.synergy if any(c in d for d in deck_set))
        if core_count > 0:
            results.append((arch, core_count, synergy_count))

    results.sort(key=lambda x: (x[1], x[2]), reverse=True)
    return results


def get_missing_cores(archetype: Archetype, deck: list[str]) -> list[str]:
    """返回该流派中当前牌组缺少的核心牌。"""
    deck_set = set(deck)
    return [c for c in archetype.core if not any(c in d for d in deck_set)]
