"""
战斗顾问：充分利用存档已有数据。

存档中可用的数据：
  monster_list          → 剩余普通怪完整队列（FIFO，顺序确定）
  elite_monster_list    → 剩余精英完整队列
  boss_list             → 全部 Boss 顺序
  metric_damage_taken   → 每场战斗实际受伤记录（用于危险度动态校准）
  metric_current_hp_per_floor → 每层结束时的血量（与 current_health 完全同步）
  metric_card_choices   → 完整选牌历史

存档中没有的数据（需 ModTheSpire）：
  战斗中当前手牌 / 敌人实时 HP / 本回合敌人意图
"""
from dataclasses import dataclass, field


# ── 房间类型 ────────────────────────────────────────────────
ROOM_ICONS = {
    "M": ("⚔️",  "普通战"),
    "E": ("💀", "精英战"),
    "B": ("👑", "Boss 战"),
    "R": ("🔥",  "营地"),
    "$": ("🛒", "商店"),
    "?": ("🎲",  "事件"),
    "T": ("💰",  "宝箱"),
}


# ── 怪物知识库 ─────────────────────────────────────────────
@dataclass
class EnemyInfo:
    name:          str
    display:       str
    base_danger:   int           # 1-5，不含动态校准
    traits:        list[str]
    strategy:      str
    avoid_cards:   list[str] = field(default_factory=list)
    priority_hint: str = ""      # 要留的牌类型


ENEMY_DB: dict[str, EnemyInfo] = {
    # ── 幕1 普通怪 ────────────────────────────────────────
    "Cultist":          EnemyInfo("Cultist",         "邪教徒",    1, ["每回合叠仪式层，后期攻击爆表"],        "首回合全力攻击秒杀",                   priority_hint="直伤牌"),
    "Jaw Worm":         EnemyInfo("Jaw Worm",         "颌虫",      2, ["首回合高伤","可能叠力量"],            "准备首回合格挡，有余力就攻击",           priority_hint="格挡牌"),
    "2 Louse":          EnemyInfo("2 Louse",          "两只虱子",  2, ["双体，AOE 效率高","红虱子有诅咒"],     "AOE 或多段，小心诅咒",                   priority_hint="AOE牌"),
    "3 Louse":          EnemyInfo("3 Louse",          "三只虱子",  3, ["三体，AOE 收益极大"],                 "AOE 或毒/闪电球",                        priority_hint="AOE牌"),
    "Small Slimes":     EnemyInfo("Small Slimes",     "小黏液",    1, ["分裂后变更多"],                       "快速清场防止分裂",                       priority_hint="直伤牌"),
    "Large Slime":      EnemyInfo("Large Slime",      "大黏液",    2, ["分裂成两小黏液"],                     "分裂前积累格挡",                         priority_hint="格挡牌"),
    "Gremlin Gang":     EnemyInfo("Gremlin Gang",     "小妖精团",  3, ["多小怪","愤怒妖精叠攻击力"],           "先杀愤怒妖精，AOE清场",                  priority_hint="AOE牌"),
    "Looter":           EnemyInfo("Looter",           "劫匪",      2, ["逃跑后偷你的金币"],                   "3回合内击杀",                            priority_hint="直伤牌"),
    "Blue Slaver":      EnemyInfo("Blue Slaver",      "蓝奴隶贩",  2, ["弱化你的攻击"],                      "格挡+快速击杀",                          priority_hint="格挡牌"),
    "Red Slaver":       EnemyInfo("Red Slaver",       "红奴隶贩",  3, ["束缚你，让牌不可使用"],               "优先击杀",                               priority_hint="直伤牌"),
    "Slavers":          EnemyInfo("Slavers",          "奴隶贩组合",3, ["束缚+弱化组合"],                     "先杀红奴隶贩解除束缚",                   priority_hint="AOE牌"),
    "Exordium Thugs":   EnemyInfo("Exordium Thugs",   "底层流氓",  2, ["双体攻击"],                          "AOE 或集火一个",                         priority_hint="AOE牌"),
    "Exordium Wildlife":EnemyInfo("Exordium Wildlife","底层野兽",  2, ["多种小型野兽混合"],                   "集火弱的先清场",                         priority_hint="AOE牌"),
    "Fungi Beast":      EnemyInfo("Fungi Beast",      "真菌兽",    2, ["死亡时施加孢子（弱化2层）"],          "普通敌人，注意弱化",                     priority_hint="直伤牌"),
    "2 Fungi Beasts":   EnemyInfo("2 Fungi Beasts",   "两只真菌兽",2, ["死亡时施加弱化","双体"],              "AOE清场或逐个击杀",                      priority_hint="AOE牌"),
    "Lots of Slimes":   EnemyInfo("Lots of Slimes",   "大量黏液怪",2, ["5只小黏液，AOE极高收益"],             "AOE一波清，单体会很累",                  priority_hint="AOE牌"),

    # ── 幕1 精英 ──────────────────────────────────────────
    "Gremlin Nob":      EnemyInfo("Gremlin Nob",      "哥布林巨人",4, ["你打技能牌他就愤怒+2攻击"],           "⚠️ 只打攻击牌！不打技能牌",              avoid_cards=["技能牌"]),
    "Lagavulin":        EnemyInfo("Lagavulin",        "拉格武林",  4, ["前3回合沉睡","唤醒后减力量/敏捷"],    "沉睡期全力堆伤，唤醒后多格挡",           priority_hint="直伤牌"),
    "Sentries":         EnemyInfo("Sentries",         "三哨兵",    3, ["轮流行动给你塞诅咒"],                 "AOE 快速清场减少诅咒",                   priority_hint="AOE牌"),
    "3 Sentries":       EnemyInfo("3 Sentries",       "三哨兵",    3, ["轮流行动给你塞诅咒"],                 "AOE 快速清场减少诅咒",                   priority_hint="AOE牌"),

    # ── 幕1 Boss ──────────────────────────────────────────
    "The Guardian":     EnemyInfo("The Guardian",     "守卫者",    4, ["护甲/攻击模式切换","进攻模式高伤"],    "护甲模式少打多段，攻击模式全力输出",     priority_hint="大单体"),
    "Hexaghost":        EnemyInfo("Hexaghost",        "六角鬼",    4, ["血越低首次技能伤害越高","强化牌变诅咒"],"开局多格挡，快速压血",                   priority_hint="格挡牌"),
    "Slime Boss":       EnemyInfo("Slime Boss",       "黏液Boss",  3, ["分裂后变两个精英级黏液"],             "分裂前积累格挡，之后 AOE",               priority_hint="AOE牌"),

    # ── 幕2 普通怪 ────────────────────────────────────────
    "Chosen":           EnemyInfo("Chosen",           "被选中者",  3, ["给你加诅咒","暗击叠层"],              "快速击杀，防止暗击堆高",                 priority_hint="直伤牌"),
    "Shell Parasite":   EnemyInfo("Shell Parasite",   "寄生贝壳",  2, ["攻击可吸血回血"],                    "全力输出一回合打完",                     priority_hint="大单体"),
    "Shelled Parasite": EnemyInfo("Shelled Parasite", "寄生贝壳",  2, ["攻击可吸血回血"],                    "全力输出一回合打完",                     priority_hint="大单体"),
    "Mugger":           EnemyInfo("Mugger",           "窃贼",      3, ["偷你的金币"],                        "3回合内击杀夺回金币",                    priority_hint="直伤牌"),
    "Byrd":             EnemyInfo("Byrd",             "鸟人",      2, ["飞行状态减伤"],                      "先用技能降低飞行层再攻击"),
    "3 Byrds":          EnemyInfo("3 Byrds",          "三只鸟人",  3, ["三体飞行减伤","AOE极有效"],           "先用技能降低飞行层，AOE清场",            priority_hint="AOE牌"),
    "Centurion and Mystic": EnemyInfo("Centurion and Mystic","百夫长+祭司",3,["祭司持续回血"],               "必须先杀祭司！",                         priority_hint="单体伤害"),
    "Centurion":        EnemyInfo("Centurion",        "百夫长",    3, ["高攻击","有治疗者辅助"],              "先杀治疗者再集火百夫长",                 priority_hint="直伤牌"),
    "Centurion and Healer": EnemyInfo("Centurion and Healer","百夫长+祭司",3,["祭司持续回血"],               "必须先杀祭司！",                         priority_hint="单体伤害"),
    "Snake Plant":      EnemyInfo("Snake Plant",      "蛇形植物",  2, ["多段攻击","受伤后反击"],              "格挡+快速击杀",                          priority_hint="格挡牌"),
    "Snecko":           EnemyInfo("Snecko",           "蛇人",      3, ["随机化你的手牌费用"],                 "全部打出手里的牌，别留牌",               avoid_cards=["留牌过多"]),
    "Spheric Guardian": EnemyInfo("Spheric Guardian", "球形守卫",  3, ["多段攻击","高格挡"],                  "等它攻击间隙输出",                       priority_hint="大单体"),
    "Sphere and 2 Shapes": EnemyInfo("Sphere and 2 Shapes","球形守卫+两形状",3,["三体","AOE收益高"],         "AOE 清场",                               priority_hint="AOE牌"),
    "2 Thieves":        EnemyInfo("2 Thieves",        "两个窃贼",  2, ["偷金币和药水"],                      "快速清场",                               priority_hint="AOE牌"),
    "Chosen and Byrds": EnemyInfo("Chosen and Byrds", "被选者+鸟人",3,["被选者给诅咒","鸟人飞行减伤"],       "先杀被选者，AOE清鸟人",                  priority_hint="AOE牌"),
    "Cultist and Chosen":EnemyInfo("Cultist and Chosen","邪教徒+被选者",3,["邪教徒叠仪式","被选者给诅咒"],   "先杀邪教徒防叠层",                       priority_hint="单体伤害"),
    "Spire Growth":     EnemyInfo("Spire Growth",     "尖塔之蔓",  3, ["每回合攻击渐强"],                    "快速击杀，拖延会很痛",                   priority_hint="直伤牌"),

    # ── 幕2 精英 ──────────────────────────────────────────
    "Book of Stabbing": EnemyInfo("Book of Stabbing", "刺杀之书",  4, ["多段伤害每回合递增"],                "堆格挡为主，速战速决",                   priority_hint="格挡牌"),
    "Gremlin Leader":   EnemyInfo("Gremlin Leader",   "哥布林首领",3, ["持续召唤小哥布林"],                  "优先秒首领，首领死后战斗结束",           priority_hint="大单体"),
    "Slavers":          EnemyInfo("Slavers",          "奴隶贩组合",4, ["束缚+弱化组合","精英级双人"],         "先杀红色奴隶贩解除束缚",                 priority_hint="AOE牌"),
    "Taskmaster":       EnemyInfo("Taskmaster",       "监工",      3, ["每回合叠虚无诅咒"],                  "快速击杀减少诅咒",                       priority_hint="直伤牌"),

    # ── 幕2 Boss ──────────────────────────────────────────
    "The Champ":        EnemyInfo("The Champ",        "冠军",      4, ["半血进入第二阶段，攻击翻倍"],          "上半段输出，下半段格挡应对高伤",         priority_hint="格挡牌"),
    "The Automaton":    EnemyInfo("The Automaton",    "自动机",    4, ["激光大招超高伤"],                     "激光前全力格挡",                         priority_hint="格挡牌"),
    "Automaton":        EnemyInfo("Automaton",        "自动机",    4, ["激光大招超高伤"],                     "激光前全力格挡",                         priority_hint="格挡牌"),
    "The Collector":    EnemyInfo("The Collector",    "收集者",    4, ["召唤火焰精英"],                       "先清火焰精英，AOE 可以同时伤害",         priority_hint="AOE牌"),

    # ── 幕3 普通怪 ────────────────────────────────────────
    "Spiker":           EnemyInfo("Spiker",           "刺球怪",    3, ["攻击它会反弹荆棘伤害"],              "毒/闪电流可绕过反伤，直接打也行",),
    "Maw":              EnemyInfo("Maw",              "巨口怪",    4, ["吞噬你的牌","高伤害"],                "保持格挡，趁攻击间隙全力输出",           priority_hint="格挡牌"),
    "Writhing Mass":    EnemyInfo("Writhing Mass",    "蠕动之物",  4, ["反应你的行动，打什么它跟什么"],       "快速击杀，越拖越难",                     priority_hint="直伤牌"),
    "Transient":        EnemyInfo("Transient",        "转瞬之物",  5, ["⚠️ 第5回合消失但扣你大量HP"],         "3-4回合内尽量打高伤害",                  priority_hint="所有伤害牌"),
    "Orb Walker":       EnemyInfo("Orb Walker",       "球体行者",  3, ["攻击+减益组合"],                     "优先格挡减益意图，有机会集火击杀",       priority_hint="格挡牌"),
    "3 Shapes":         EnemyInfo("3 Shapes",         "三个形体",  3, ["三体，AOE收益高"],                   "AOE 清场",                               priority_hint="AOE牌"),
    "4 Shapes":         EnemyInfo("4 Shapes",         "四个形体",  3, ["四体，AOE收益极高"],                 "AOE 清场",                               priority_hint="AOE牌"),
    "Jaw Worm Horde":   EnemyInfo("Jaw Worm Horde",   "颌虫群",    3, ["多只颌虫，AOE收益极高"],             "AOE一波清",                              priority_hint="AOE牌"),
    "Spire Shield and Spire Spear": EnemyInfo("Spire Shield and Spire Spear","尖塔盾+矛",4,["盾格挡极高","矛高频攻击"],"先杀矛再处理盾",priority_hint="单体伤害"),
    "Spire Shield":     EnemyInfo("Spire Shield",     "尖塔之盾",  3, ["极高格挡"],                         "穿透或毒/闪电流绕过格挡"),
    "Spire Spear":      EnemyInfo("Spire Spear",      "尖塔之矛",  4, ["高频率攻击"],                       "堆格挡应对",                             priority_hint="格挡牌"),

    # ── 幕3 精英 ──────────────────────────────────────────
    "Reptomancer":      EnemyInfo("Reptomancer",      "蛇女巫",    4, ["召唤蛇仆，满4条时爆发"],             "AOE 清蛇仆，不让堆满",                   priority_hint="AOE牌"),
    "Giant Head":       EnemyInfo("Giant Head",       "巨像头颅",  4, ["倒计时叠层，越晚伤害越大"],           "全力快速输出，拖到后期必死",             priority_hint="最高输出"),
    "Nemesis":          EnemyInfo("Nemesis",          "宿敌",      5, ["隐身时免疫伤害","会给你塞诅咒"],     "隐身时防御，现身时全力输出"),

    # ── 幕3 Boss ──────────────────────────────────────────
    "Time Eater":       EnemyInfo("Time Eater",       "时间吞噬者",5, ["你每打12张牌它行动一次大招"],         "⚠️ 控制每回合出牌数，一次性爆发",        avoid_cards=["大量零费牌"]),
    "The Awakened One": EnemyInfo("The Awakened One", "觉醒者",    5, ["你打能力牌它叠力量","死后复活"],       "第一阶段少打能力牌，第二阶段全力输出",   priority_hint="攻击牌为主", avoid_cards=["大量能力牌"]),
    "Awakened One":     EnemyInfo("Awakened One",     "觉醒者",    5, ["你打能力牌它叠力量","死后复活"],       "第一阶段少打能力牌，第二阶段全力输出",   priority_hint="攻击牌为主", avoid_cards=["大量能力牌"]),
    "Donu and Deca":    EnemyInfo("Donu and Deca",    "多努与迪卡",5, ["两个同时活着互相增强"],               "集中火力秒一个，拆掉组合",               priority_hint="单体大伤害"),
    "The Heart":        EnemyInfo("The Heart",        "腐化之心",  5, ["首回合超高伤害","固定循环模式"],       "第一回合必须大量格挡！然后叠毒/力量",    priority_hint="格挡牌（第1回合）"),
    "3 Darklings":      EnemyInfo("3 Darklings",      "三暗灵",    4, ["全灭同回合才死，否则复活"],           "AOE同时打低再同回合清掉",               priority_hint="AOE牌"),
}


def get_enemy_info(name: str) -> EnemyInfo | None:
    """按英文 key 或中文 display 或模糊匹配查询"""
    if name in ENEMY_DB:
        return ENEMY_DB[name]
    # 按中文 display 精确匹配
    for info in ENEMY_DB.values():
        if info.display == name:
            return info
    # 模糊匹配（英文 key 或中文 display 包含关系）
    name_l = name.lower()
    for key, info in ENEMY_DB.items():
        if key.lower() in name_l or name_l in key.lower():
            return info
        if info.display in name or name in info.display:
            return info
    return None


# ── 动态危险度校准 ─────────────────────────────────────────
def calibrate_danger(enemy_name: str, damage_history: list[dict]) -> int:
    """
    根据玩家历史受伤记录，动态调整危险等级。
    同一敌人受伤越多 → 危险度+1（最多+2）
    """
    info = get_enemy_info(enemy_name)
    base = info.base_danger if info else 3
    past = [x for x in damage_history
            if enemy_name.lower() in x.get("enemies","").lower()
            or x.get("enemies","").lower() in enemy_name.lower()]
    if not past:
        return base
    avg_dmg = sum(x.get("damage", 0) for x in past) / len(past)
    if avg_dmg > 30:
        return min(5, base + 2)
    if avg_dmg > 15:
        return min(5, base + 1)
    return base


# ── 未来遭遇队列 ──────────────────────────────────────────
@dataclass
class UpcomingFight:
    floor:      int | None   # None = 还不知道具体楼层
    room_type:  str          # M / E / B
    enemy_name: str
    danger:     int
    info:       EnemyInfo | None


def get_upcoming_fights(save_data: dict, max_count: int = 5) -> list[UpcomingFight]:
    """
    从存档直接读取即将到来的战斗队列。
    monster_list / elite_monster_list / boss_list 已经是 FIFO 顺序，
    不依赖路径预测，直接按队列返回。
    """
    damage_history = save_data.get("metric_damage_taken", [])
    monsters = list(save_data.get("monster_list", []))
    elites   = list(save_data.get("elite_monster_list", []))
    bosses   = list(save_data.get("boss_list", []))
    results  = []

    # 先把三个队列合并，按"最可能的遭遇顺序"输出：
    # 通常是 M → E → M → ... → B
    # 用 metric_path_per_floor 剩余部分推算顺序
    path       = save_data.get("metric_path_per_floor", [])
    floor_num  = save_data.get("floor_num", 0)
    future_path = path[floor_num:]   # 当前层之后的路径（已完成的路不含）

    m_idx = e_idx = b_idx = 0
    for room_type in future_path:
        if len(results) >= max_count:
            break
        if room_type == "M" and m_idx < len(monsters):
            name = monsters[m_idx]; m_idx += 1
        elif room_type == "E" and e_idx < len(elites):
            name = elites[e_idx]; e_idx += 1
        elif room_type == "B" and b_idx < len(bosses):
            name = bosses[b_idx]; b_idx += 1
        else:
            continue
        info   = get_enemy_info(name)
        danger = calibrate_danger(name, damage_history)
        results.append(UpcomingFight(
            floor=None, room_type=room_type,
            enemy_name=name, danger=danger, info=info,
        ))

    # 若 path 已用完但队列还有（后续楼层未走），继续追加
    if len(results) < max_count:
        for name in monsters[m_idx:]:
            if len(results) >= max_count: break
            info = get_enemy_info(name)
            results.append(UpcomingFight(None, "M", name,
                                         calibrate_danger(name, damage_history), info))
        for name in elites[e_idx:]:
            if len(results) >= max_count: break
            info = get_enemy_info(name)
            results.append(UpcomingFight(None, "E", name,
                                         calibrate_danger(name, damage_history), info))
        for name in bosses[b_idx:]:
            if len(results) >= max_count: break
            info = get_enemy_info(name)
            results.append(UpcomingFight(None, "B", name,
                                         calibrate_danger(name, damage_history), info))

    return results


def build_combat_alert(fight: UpcomingFight) -> str:
    """生成单场战斗预告文本"""
    icons = {"M": "⚔️", "E": "💀", "B": "👑"}
    labels = {"M": "普通战", "E": "精英战", "B": "Boss战"}
    icon  = icons.get(fight.room_type, "⚔️")
    label = labels.get(fight.room_type, "战斗")
    name  = fight.info.display if fight.info else fight.enemy_name
    danger_bar = "🔴" * fight.danger + "⚫" * (5 - fight.danger)

    lines = [f"{icon} {label}：{name}  {danger_bar}"]
    if fight.info:
        if fight.info.traits:
            lines.append(f"📌 {fight.info.traits[0]}")
        lines.append(f"💡 {fight.info.strategy}")
        if fight.info.avoid_cards:
            lines.append(f"⚠️ 避免：{', '.join(fight.info.avoid_cards[:1])}")
    return "\n".join(lines)


def post_combat_advice(save_data: dict, character: str) -> list[str]:
    """战斗/选牌后的牌组调整建议"""
    from core.archetypes import identify_archetype, get_missing_cores
    from core.decoder import parse_deck

    deck    = parse_deck(save_data)
    matches = identify_archetype(character, deck)
    tips    = []

    if not matches:
        tips.append("💡 牌组尚无明确流派，优先选择有协同的牌")
        return tips

    top_arch, core_cnt, _ = matches[0]
    missing = get_missing_cores(top_arch, deck)

    if missing:
        tips.append(f"🎯 优先拿取核心牌：{', '.join(missing)}")
    if len(deck) > 20:
        tips.append(f"🗑️ 牌组 {len(deck)} 张偏多，考虑移除弱牌")
    if core_cnt == len(top_arch.core):
        tips.append(f"✅ {top_arch.name} 核心齐，专注协同：{', '.join(top_arch.synergy[:2])}")

    return tips


# ── 向后兼容（供旧 main.py 调用）──────────────────────────
def build_briefing(save_data: dict, room_class: str):
    """兼容旧接口，返回 None（已由 get_upcoming_fights 替代）"""
    return None


def parse_room_type(class_name: str) -> str:
    from core.watcher import SaveState
    for key, val in {
        "MonsterRoom":      "monster",
        "MonsterRoomElite": "elite",
        "MonsterRoomBoss":  "boss",
        "EventRoom":        "event",
        "ShopRoom":         "shop",
        "RestRoom":         "rest",
        "TreasureRoom":     "treasure",
    }.items():
        if key in class_name:
            return val
    return "unknown"
