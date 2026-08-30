"""Persistent, append-only review state store for JARVIS workflows."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .review_state import ReviewState, ReviewStateMachine, ReviewTransition


class PersistentReviewStateStore:
    """Persist review state machines as a rebuildable JSONL event stream."""

    def __init__(self, path: str | Path = ".jarvis/review_states.jsonl") -> None:
        self.path = Path(path).expanduser()

    def _records(self) -> dict[str, dict[str, Any]]:
        states: dict[str, dict[str, Any]] = {}
        if not self.path.is_file():
            return states
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    item = json.loads(line)
                    case_id = str(item.get("case_id") or "")
                    if case_id:
                        states[case_id] = item
        except (OSError, json.JSONDecodeError):
            return {}
        return states

    def _append(self, item: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def get(self, case_id: str) -> dict[str, Any] | None:
        return self._records().get(str(case_id))

    def ensure_open(self, case_id: str) -> ReviewStateMachine:
        existing = self.get(case_id)
        if existing:
            return ReviewStateMachine(case_id=case_id, state=ReviewState(str(existing["state"])))
        machine = ReviewStateMachine(case_id=case_id)
        self._append(machine.as_dict())
        return machine

    def transition(self, case_id: str, target: ReviewState | str, *, actor: str, reason: str) -> ReviewTransition:
        machine = self.ensure_open(case_id)
        transition = machine.transition(target, actor=actor, reason=reason)
        self._append({**transition.as_dict(), "state": machine.state.value, "can_apply_mutation": machine.can_apply_mutation()})
        return transition

    def snapshot(self, case_id: str) -> dict[str, Any]:
        existing = self.get(case_id)
        if existing:
            return dict(existing)
        return self.ensure_open(case_id).as_dict()

    def all(self) -> list[dict[str, Any]]:
        return list(self._records().values())
