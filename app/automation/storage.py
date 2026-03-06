from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict


BASE_DIR = Path(__file__).resolve().parent / "data"
RULES_FILE = BASE_DIR / "automation_rules.json"
IO_NAMES_FILE = BASE_DIR / "io_names.json"


class JsonStorage:
    def __init__(self, file_path: Path, default_data: Dict[str, Any]):
        self.file_path = file_path
        self.default_data = default_data
        self._lock = threading.Lock()
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.write(self.default_data)

    def read(self) -> Dict[str, Any]:
        with self._lock:
            if not self.file_path.exists():
                return dict(self.default_data)
            with self.file_path.open("r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    return dict(self.default_data)
            if not isinstance(data, dict):
                return dict(self.default_data)
            return data

    def write(self, data: Dict[str, Any]) -> None:
        with self._lock:
            temp_path = self.file_path.with_suffix(self.file_path.suffix + ".tmp")
            with temp_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=True, indent=2)
            temp_path.replace(self.file_path)


rules_storage = JsonStorage(RULES_FILE, {"rules": []})
io_names_storage = JsonStorage(IO_NAMES_FILE, {"inputs": {}, "outputs": {}})
