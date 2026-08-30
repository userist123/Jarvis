"""Tkinter conflict review workflow bound to authenticated reviewer identity."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any

from .authenticated_reviewer import AuthenticatedReviewer
from .reviewer_identity import ReviewerIdentity


class ConflictReviewerWindow(tk.Toplevel):
    """Operator UI for conflict evidence and verdict workflow."""

    def __init__(self, parent: tk.Misc, gateway: Any, identity: ReviewerIdentity):
        super().__init__(parent)
        self.gateway = gateway
        self.reviewer = AuthenticatedReviewer(identity, gateway)
        self.identity = identity
        self.title("JARVIS - Conflict Review")
        self.geometry("1080x760")
        self.minsize(900, 640)
        self.case: dict[str, Any] = {}
        self.bundle: dict[str, Any] = {}
        self.verification: dict[str, Any] = {}
        self.verdict: dict[str, Any] = {}
        self.decision_state: dict[str, Any] = {}
        self._build()

    def _build(self) -> None:
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="Conflict Review", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Label(toolbar, text=f"Identity: {self.identity.subject or 'none'} / {self.identity.principal.value}").pack(side="left", padx=16)

        controls = ttk.Frame(self, padding=(8, 0, 8, 8))
        controls.pack(fill="x")
        ttk.Label(controls, text="Memory IDs (comma separated):").grid(row=0, column=0, sticky="w")
        self.memory_ids = tk.StringVar()
        ttk.Entry(controls, textvariable=self.memory_ids, width=60).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Label(controls, text="Conflict type:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.conflict_type = tk.StringVar(value="semantic")
        ttk.Entry(controls, textvariable=self.conflict_type, width=30).grid(row=1, column=1, sticky="w", padx=6, pady=(6, 0))
        ttk.Label(controls, text="Reasons:").grid(row=2, column=0, sticky="nw", pady=(6, 0))
        self.reasons = tk.Text(controls, height=3, width=60)
        self.reasons.grid(row=2, column=1, sticky="ew", padx=6, pady=(6, 0))
        controls.columnconfigure(1, weight=1)

        buttons = ttk.Frame(self, padding=(8, 0, 8, 8))
        buttons.pack(fill="x")
        self._button(buttons, "Open Case", self._open_case, 0)
        self._button(buttons, "Acquire Evidence", self._acquire_evidence, 1)
        self._button(buttons, "Verify Evidence", self._verify_evidence, 2)
        self._button(buttons, "Approve A", lambda: self._issue_verdict("ACCEPT_A"), 3)
        self._button(buttons, "Approve B", lambda: self._issue_verdict("ACCEPT_B"), 4)
        self._button(buttons, "Defer", lambda: self._issue_verdict("DEFER"), 5)
        self._button(buttons, "Apply Decision", self._apply_decision, 6)
        self.apply_button = buttons.winfo_children()[-1]

        self.details = ScrolledText(self, wrap="word", state="disabled", font=("Consolas", 10))
        self.details.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.status = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status).pack(fill="x", padx=8, pady=(0, 8))

    @staticmethod
    def _button(parent: ttk.Frame, text: str, command: Any, column: int) -> None:
        ttk.Button(parent, text=text, command=command).grid(row=0, column=column, padx=(0, 6))

    def load_case(self, case_id: str) -> None:
        """Load an existing conflict case without creating or mutating it."""
        try:
            state = self.gateway.get_review_state(case_id)
            self.case = {"case_id": case_id, "review_state": state}
            self.decision_state = dict(state)
            self.status.set(f"Loaded: {case_id} / {state.get('state', '-')}")
            self._show(self.case)
            self._update_controls()
        except Exception as exc:
            self._error(exc)

    def _ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(x.strip() for x in self.memory_ids.get().split(",") if x.strip()))

    def _open_case(self) -> None:
        ids = self._ids()
        if len(ids) < 2:
            messagebox.showerror("Conflict Review", "At least two memory IDs are required.", parent=self)
            return
        try:
            reasons = tuple(line.strip() for line in self.reasons.get("1.0", "end").splitlines() if line.strip())
            self.case = self.gateway.open_conflict_review(memory_ids=ids, reasons=reasons, conflict_type=self.conflict_type.get().strip() or "semantic")
            self.decision_state = dict(self.case.get("review_state") or {})
            self.status.set(f"Opened: {self.case.get('case_id', '-')} / {self.decision_state.get('state', 'OPEN')}")
            self._show(self.case)
            self._update_controls()
        except Exception as exc:
            self._error(exc)

    def _acquire_evidence(self) -> None:
        case_id = str(self.case.get("case_id") or "")
        if not case_id:
            messagebox.showerror("Conflict Review", "Open a case first.", parent=self)
            return
        try:
            self.bundle = self.gateway.acquire_conflict_evidence(memory_ids=self._ids(), conflict_case_id=case_id)
            self.status.set("Evidence acquired")
            self._show(self.bundle)
            self._update_controls()
        except Exception as exc:
            self._error(exc)

    def _verify_evidence(self) -> None:
        if not self.bundle:
            messagebox.showerror("Conflict Review", "Acquire evidence first.", parent=self)
            return
        try:
            result = self.gateway.verify_and_advance_conflict_review(bundle=self.bundle)
            self.verification = dict(result.get("verification") or {})
            self.decision_state = dict(result.get("review_state") or {})
            self.status.set(f"Evidence valid: {self.verification.get('valid', False)} / state={self.decision_state.get('state', '-')}")
            self._show(result)
            self._update_controls()
        except Exception as exc:
            self._error(exc)

    def _issue_verdict(self, verdict: str) -> None:
        if not self.identity.can_decide:
            messagebox.showerror("Conflict Review", "Authenticated HUMAN/ADMIN reviewer identity is required.", parent=self)
            return
        if not self.verification.get("valid"):
            messagebox.showerror("Conflict Review", "Valid verified evidence is required.", parent=self)
            return
        case_id = str(self.bundle.get("conflict_case_id") or self.case.get("case_id") or "")
        if not case_id:
            return
        try:
            self.verdict = self.reviewer.issue_conflict_verdict(
                verdict=verdict, memory_ids=self._ids(),
                evidence_bundle_hash=str(self.bundle.get("bundle_hash") or ""),
                evidence_valid=True, reason="Reviewer decision from Conflict Review UI",
                as_of=self.bundle.get("as_of"), known_as_of=self.bundle.get("known_as_of"),
            )
            target_state = "DEFERRED" if verdict == "DEFER" else "APPROVED"
            self.decision_state = self.reviewer.transition_review_state(case_id=case_id, target=target_state, reason=f"Reviewer issued {verdict}")
            self.status.set(f"Verdict issued: {verdict} / state={target_state}")
            self._show({"verdict": self.verdict, "review_state": self.decision_state})
            self._update_controls()
        except Exception as exc:
            self._error(exc)

    def _apply_decision(self) -> None:
        if not self.verdict:
            messagebox.showerror("Conflict Review", "Issue a verdict first.", parent=self)
            return
        if self.verdict.get("verdict") == "DEFER":
            self.status.set("Decision deferred; no memory mutation performed")
            self._show({"verdict": self.verdict, "review_state": self.decision_state, "mutation": "skipped"})
            return
        if self.decision_state.get("state") != "APPROVED":
            messagebox.showerror("Conflict Review", "Review state must be APPROVED before mutation.", parent=self)
            return
        try:
            result = self.reviewer.apply_conflict_verdict(
                verdict=self.verdict, evidence_verification=self.verification,
                review_state=self.decision_state, action="attest",
                reason="Apply authorized conflict decision",
            )
            self.status.set("Mutation result received")
            self._show(result)
        except Exception as exc:
            self._error(exc)

    def _update_controls(self) -> None:
        self.apply_button.configure(state="normal" if self.identity.can_decide and self.verdict and self.decision_state.get("state") == "APPROVED" else "disabled")

    def _error(self, exc: Exception) -> None:
        self.status.set(f"Error: {exc}")
        self._show({"error": str(exc)})
        self._update_controls()

    def _show(self, payload: dict[str, Any]) -> None:
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("end", json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        self.details.configure(state="disabled")


def open_conflict_reviewer_window(parent: tk.Misc, gateway: Any, identity: ReviewerIdentity) -> ConflictReviewerWindow:
    return ConflictReviewerWindow(parent, gateway, identity)
