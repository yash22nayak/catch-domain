"""JSON-file cache so reruns only perform checks that are new."""
import json
import time
from pathlib import Path
from typing import Any


class Cache:
    """Keyed '<check_type>:<target>'; each entry stores the value and a timestamp."""

    def __init__(self, path: Path, refresh: bool = False):
        self.path = Path(path)
        self._data: dict[str, dict] = {}
        if not refresh and self.path.exists():
            self._data = json.loads(self.path.read_text(encoding="utf-8"))

    def get(self, key: str) -> Any | None:
        entry = self._data.get(key)
        return entry["value"] if entry else None

    def set(self, key: str, value: Any) -> None:
        self._data[key] = {"value": value, "ts": time.time()}

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=1), encoding="utf-8")
