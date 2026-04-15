"""
Decode and parse STS autosave files.
STS saves are base64(XOR(json, 'key')).
"""
import base64
import json
import os

SAVE_DIR = r"C:\Program Files (x86)\Steam\steamapps\common\SlayTheSpire\saves"
RUN_DIR  = r"C:\Program Files (x86)\Steam\steamapps\common\SlayTheSpire\runs"

CHARACTER_FILES = {
    "IRONCLAD":  "IRONCLAD.autosave",
    "THE_SILENT": "THE_SILENT.autosave",
    "DEFECT":    "DEFECT.autosave",
    "WATCHER":   "WATCHER.autosave",
}

def decode_save(path: str) -> dict | None:
    """解密并解析一个 .autosave 文件，返回 dict，失败返回 None。"""
    try:
        with open(path, "rb") as f:
            raw = f.read()
        decoded = base64.b64decode(raw)
        key = b"key"
        xored = bytes(b ^ key[i % 3] for i, b in enumerate(decoded))
        return json.loads(xored.decode("utf-8"))
    except Exception:
        return None


def get_active_save() -> tuple[str, dict] | tuple[None, None]:
    """
    遍历四个角色的存档，返回最近修改的那个。
    返回 (character_key, save_data)，没有存档时返回 (None, None)。
    """
    best_path = None
    best_mtime = 0
    best_char = None

    for char, filename in CHARACTER_FILES.items():
        path = os.path.join(SAVE_DIR, filename)
        if os.path.exists(path):
            mtime = os.path.getmtime(path)
            if mtime > best_mtime:
                best_mtime = mtime
                best_path = path
                best_char = char

    if best_path is None:
        return None, None

    data = decode_save(best_path)
    return best_char, data


def get_save_path(char: str) -> str:
    filename = CHARACTER_FILES.get(char, f"{char}.autosave")
    return os.path.join(SAVE_DIR, filename)


def get_all_save_paths() -> list[str]:
    return [
        os.path.join(SAVE_DIR, fn)
        for fn in CHARACTER_FILES.values()
        if os.path.exists(os.path.join(SAVE_DIR, fn))
    ]


def parse_deck(save_data: dict) -> list[str]:
    """从存档中提取牌组 ID 列表。"""
    cards = save_data.get("cards", [])
    if cards and isinstance(cards[0], dict):
        return [c.get("id", "") for c in cards]
    return list(cards)


def parse_upgraded_ids(save_data: dict) -> dict[str, int]:
    """返回已升级的卡牌ID→升级副本数量。
    用 dict 计数而非 set，以便正确处理同一张牌有多张副本的情况。
    例如 2 张 Barricade，1 张已升级 → {"Barricade": 1}
    """
    cards = save_data.get("cards", [])
    upgraded: dict[str, int] = {}
    for c in cards:
        if isinstance(c, dict) and c.get("upgrades", 0) > 0:
            cid = c.get("id", "")
            upgraded[cid] = upgraded.get(cid, 0) + 1
    return upgraded


def parse_relics(save_data: dict) -> list[str]:
    """提取遗物 ID 列表。"""
    relics = save_data.get("relics", [])
    if relics and isinstance(relics[0], dict):
        return [r.get("id", "") for r in relics]
    return list(relics)
