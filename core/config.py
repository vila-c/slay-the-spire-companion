"""
Player settings persistence.
Stores user preferences (nickname, UI toggles) in a JSON file.
"""
import json
import os

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json"
)

_DEFAULTS = {
    "player_name": "主人",
    "chat_bubble_enabled": True,
    "extreme_tips_enabled": True,
}

_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is not None:
        return _cache
    try:
        with open(_CONFIG_PATH, encoding="utf-8") as f:
            _cache = {**_DEFAULTS, **json.load(f)}
    except Exception:
        _cache = dict(_DEFAULTS)
    return _cache


def get(key: str):
    return _load().get(key, _DEFAULTS.get(key))


def set_val(key: str, value):
    cfg = _load()
    cfg[key] = value
    _save(cfg)


def _save(cfg: dict):
    global _cache
    _cache = cfg
    os.makedirs(os.path.dirname(_CONFIG_PATH), exist_ok=True)
    with open(_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
