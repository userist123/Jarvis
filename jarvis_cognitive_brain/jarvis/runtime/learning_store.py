"""Persistent, rebuildable storage for derived JARVIS learning cases."""

from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
from typing import Any

from jarvis.runtime.learning_dedup import LearningCase


class PersistentLearningStore:
    """Persist derived learning observations without becoming canonical memory."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()

    def save(self, cases: list[LearningCase]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = [case.as_dict() for case in cases]
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    def load(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return data if isinstance(data, list) else []

    def upsert(self, case: LearningCase) -> None:
        current = {str(item.get("case_id")): item for item in self.load() if item.get("case_id")}
        current[case.case_id] = case.as_dict()
        self._write_records(list(current.values()))

    def _write_records(self, records: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(records, indent=2, sort_keys=True, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self.path)

    def records(self) -> list[dict[str, Any]]:
        return self.load()
