"""JARVIS-side conflict review facade.

Creates review cases and read-only evidence snapshots from the canonical Vault.
Resolution remains an explicit authorized operation in the Vault.
"""

from __future__ import annotations

from typing import Any, Iterable


class ConflictReviewService:
    def __init__(self, vault_bridge: Any) -> None:
        self.vault_bridge = vault_bridge

    def _controller(self) -> Any:
        if not getattr(self.vault_bridge, "available", False):
            raise RuntimeError("Canonical Vault is unavailable")
        backend = getattr(self.vault_bridge, "_backend", None)
        controller = getattr(backend, "controller", None)
        if controller is None:
            raise RuntimeError("Canonical MemoryController is unavailable")
        return controller

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
        self._controller()
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

    def acquire_evidence(
        self,
        *,
        memory_ids: Iterable[str],
        conflict_case_id: str | None = None,
        as_of: Any = None,
        known_as_of: Any = None,
    ) -> dict[str, Any]:
        """Build a hash-verifiable, read-only evidence snapshot from canonical reads."""
        controller = self._controller()
        try:
            from memory_controller.evidence_bundle import build_evidence_bundle
        except Exception as exc:
            raise RuntimeError("Canonical evidence bundle builder is unavailable") from exc

        ids = tuple(dict.fromkeys(str(x) for x in memory_ids if x))
        if len(ids) < 2:
            raise ValueError("At least two memory IDs are required")

        notes: list[dict[str, Any]] = []
        for note_id in ids:
            try:
                pack = controller.cognitive_read(
                    getattr(self.vault_bridge._backend, "principal"),
                    note_id,
                )
            except Exception as exc:
                raise RuntimeError(f"Unable to acquire evidence for memory {note_id}") from exc
            results = list(pack.get("results", pack.get("items", [])))
            if not results:
                raise ValueError(f"Memory {note_id} was not readable for evidence acquisition")
            notes.append(dict(results[0]))

        return build_evidence_bundle(
            notes,
            conflict_case_id=conflict_case_id,
            evidence_ids=ids,
            as_of=as_of,
            known_as_of=known_as_of,
        )

    def verify_evidence(
        self,
        *,
        bundle: dict[str, Any],
    ) -> dict[str, Any]:
        """Re-read canonical memories and verify bundle integrity without mutation."""
        controller = self._controller()
        try:
            from memory_controller.evidence_verifier import verify_evidence_bundle
        except Exception as exc:
            raise RuntimeError("Canonical evidence verifier is unavailable") from exc

        principal = getattr(self.vault_bridge._backend, "principal")
        notes: list[dict[str, Any]] = []
        for item in bundle.get("items", []):
            note_id = str(item.get("memory_id") or "")
            if not note_id:
                continue
            try:
                pack = controller.cognitive_read(principal, note_id)
            except Exception:
                continue
            results = list(pack.get("results", pack.get("items", [])))
            if results:
                notes.append(dict(results[0]))
        return verify_evidence_bundle(bundle, notes).as_dict()
