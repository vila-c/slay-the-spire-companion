"""
Shop advisor - strategy-based advice for shop visits.
Focus on WHAT TYPE of purchase to prioritize, not specific items
(since we can't see the actual shop inventory).
"""
from core.archetypes import identify_archetype, ARCHETYPES
from core.decoder import parse_deck, parse_relics
from core.scorer import CURSE_CARDS


def get_shop_advice(character: str, save_data: dict) -> dict:
    """
    Returns shop advice dict:
      priorities: list of (action, reason)
      summary: one-line summary for chat bubble
      budget_tip: spending strategy
      gold: current gold
    """
    deck = parse_deck(save_data)
    relics = parse_relics(save_data)
    gold = save_data.get("gold", 0) or 0
    hp = save_data.get("current_health", 0) or 0
    max_hp = save_data.get("max_health", 1) or 1
    floor = save_data.get("floor_num", 0)

    arch_matches = identify_archetype(character, deck)
    top_arch = arch_matches[0][0] if arch_matches else None

    priorities = []

    # 1. Remove curses (always available, ~50g)
    curse_count = sum(1 for c in deck if any(curse in c for curse in CURSE_CARDS))
    if curse_count > 0 and gold >= 50:
        priorities.append(("移除诅咒", f"有{curse_count}张诅咒，优先花钱净化"))

    # 2. Remove strikes (always available, ~75g)
    strike_count = sum(1 for c in deck if "Strike" in c)
    if strike_count >= 3 and gold >= 75:
        priorities.append(("移除打击", f"还有{strike_count}张打击，移除提升牌组质量"))

    # 3. General strategy based on deck state
    deck_size = len(deck)
    hp_ratio = hp / max(max_hp, 1)

    if deck_size > 25:
        priorities.append(("精简牌组", "牌组超过25张，优先移除弱牌而非买新牌"))
    elif top_arch:
        from core.archetypes import get_missing_cores
        missing = get_missing_cores(top_arch, deck)
        if missing:
            priorities.append(("补全核心", f"{top_arch.name}还缺核心牌，留意商店卡牌"))

    # 4. Relic general advice
    if gold >= 150:
        if floor <= 20:
            priorities.append(("留意遗物", "前期遗物收益最大，如果有好遗物值得投资"))
        elif not any(p[0] == "移除诅咒" for p in priorities):
            priorities.append(("看遗物", "金币充裕，关注有用的遗物"))

    # 5. Potion advice
    if hp_ratio < 0.4 and gold >= 50:
        priorities.append(("买药水", "血量偏低，回血药水保命"))

    # Budget tip
    if gold < 100:
        budget = "金币紧张，只买最必要的（移除牌最优先）"
    elif gold < 200:
        budget = "金币一般，精打细算"
    elif gold < 350:
        budget = "金币充裕，可以适当投资"
    else:
        budget = "金币富余，大胆购物！"

    # Summary for chat bubble
    if priorities:
        summary = priorities[0][1]
    else:
        summary = "商店没什么必买的，存钱也行"

    return {
        "priorities": priorities[:4],
        "summary": summary,
        "budget_tip": budget,
        "gold": gold,
    }
