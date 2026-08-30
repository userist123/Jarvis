"""JARVIS-side conflict review facade.

Creates review cases from Vault conflict metadata without mutating canonical
memory. Resolution remains an explicit authorized operation in the Vault.
"""

from __future__ import annotations

from typing import Any, Iterable


class ConflictReviewService:
    def __init__(self, vault_bridge: Any) -> None:
        self.vault_bridge = vault_bridge

    def open_case(
        self,
        *,
        memory_ids: Iterable[str],
        reasons: Iterable[str],
        conflict_type: str = "semantic",
        evidence_ids: Iterable[str] = (),
        as_of: Any = None,
        known_as_of: Any = None,
    ) -> dict[str, Any]:
        if not getattr(self.vault_bridge, "available", False):
            raise RuntimeError("Canonical Vault is unavailable")
        backend = getattr(self.vault_bridge, "_backend", None)
        controller = getattr(backend, "controller", None)
        if controller is None:
            raise RuntimeError("Canonical MemoryController is unavailable")
        try:
            from memory_controller.conflict_review import ConflictReviewWorkflow
        except Exception as exc:
            raise RuntimeError("Canonical conflict review workflow is unavailable") from exc
        workflow = ConflictReviewWorkflow()
        return workflow.open_case(
            memory_ids=memory_ids,
            reasons=reasons,
            conflict_type=conflict_type,
            evidence_ids=evidence_ids,
            as_of=as_of,
            known_as_of=known_as_of,
        ).as_dict()
