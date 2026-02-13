import json
from pathlib import Path

def load_topics(path: str = "app/config/topics.json") -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {p}")
    data = json.loads(p.read_text(encoding="utf-8"))

    topics = data.get("topics", [])
    if not isinstance(topics, list) or len(topics) == 0:
        raise ValueError("topics must be a non-empty list")

    ids = set()
    for t in topics:
        tid = t.get("id")
        if not tid or not isinstance(tid, str):
            raise ValueError("Each topic must have a string 'id'")
        if tid in ids:
            raise ValueError(f"Duplicate topic id: {tid}")
        ids.add(tid)

        sources = t.get("sources", [])
        if not isinstance(sources, list) or len(sources) == 0:
            raise ValueError(f"Topic '{tid}' must have a non-empty sources list")

        for s in sources:
            if "url" not in s or "name" not in s:
                raise ValueError(f"Topic '{tid}' sources must contain name + url")

    return data
