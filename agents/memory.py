import json
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

MEMORY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "shared_memory.json"
)

_DEFAULT = {
    "conversation_summaries": [],
    "learned_preferences": [],
    "contact_notes": {},
    "task_history": [],
}


def _ensure_file():
    os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
    if not os.path.exists(MEMORY_PATH):
        with open(MEMORY_PATH, "w") as fh:
            json.dump(_DEFAULT, fh, indent=2)


def load() -> dict:
    _ensure_file()
    with open(MEMORY_PATH, "r") as fh:
        data = json.load(fh)
    logger.debug("memory load: %d history items", len(data.get("task_history", [])))
    return data


def save(data: dict):
    _ensure_file()
    with open(MEMORY_PATH, "w") as fh:
        json.dump(data, fh, indent=2, default=str)
    logger.debug("memory save: ok")


def append_history(entry: dict):
    data = load()
    entry.setdefault("ts", datetime.utcnow().isoformat())
    data["task_history"].append(entry)
    data["task_history"] = data["task_history"][-200:]
    save(data)


def add_learned_preference(rule: str):
    data = load()
    if rule not in data["learned_preferences"]:
        data["learned_preferences"].append(rule)
        save(data)


def get_preferences() -> list:
    return load().get("learned_preferences", [])


def get_recent_history(n: int = 10) -> list:
    return load().get("task_history", [])[-n:]
