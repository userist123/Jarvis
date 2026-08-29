from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Mapping


class TelemetryJournal:
    """Append-only local JSONL telemetry with content redaction by default."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def record(self, event: str, *, payload: Mapping[str, Any] | None = None, include_content: bool = False) -> None:
        data = dict(payload or {})
        if not include_content:
            for key in ("prompt", "response", "content", "raw_text"):
                data.pop(key, None)
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "event": event,
            "payload": data,
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")
