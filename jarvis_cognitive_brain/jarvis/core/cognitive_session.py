"""Ephemeral JARVIS session checkpoint backed by the canonical Vault Executive.

Only lightweight state is persisted here: session id, user goal, active note
IDs/activation scores, and the current plan reference. Canonical note content
is never copied into the checkpoint; rehydration is delegated to the Vault
Executive/MemoryController.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass
class CognitiveSession:
    session_id: str = field(default_factory=lambda: uuid4().hex)
    goal: str = ""
    active_nodes: list[dict[str, Any]] = field(default_factory=list)
    plan_id: str | None = None
    tick: int = 0

    def checkpoint(self, path: str | Path) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(self)
        tmp = target.with_suffix(target.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(target)
        return target

    @classmethod
    def restore(cls, path: str | Path) -> "CognitiveSession":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            session_id=str(payload["session_id"]),
            goal=str(payload.get("goal", "")),
            active_nodes=list(payload.get("active_nodes", [])),
            plan_id=payload.get("plan_id"),
            tick=int(payload.get("tick", 0)),
        )

    def record_activation(self, note_id: str, score: float) -> None:
        self.active_nodes = [n for n in self.active_nodes if n.get("id") != note_id]
        self.active_nodes.append({"id": note_id, "activation": float(score)})
