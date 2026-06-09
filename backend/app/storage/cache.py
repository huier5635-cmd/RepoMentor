from __future__ import annotations

from pathlib import Path
from typing import Any

import json


class JsonCache:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Any | None:
        path = self.root / f"{key}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def set(self, key: str, value: Any) -> None:
        path = self.root / f"{key}.json"
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
