"""Tkinter reviewer window backed by JARVIS review contracts."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any, Callable

from .reviewer_identity import ReviewerIdentity


class ReviewerWindow(tk.Toplevel):
    """Policy-aware learning review UI; authoritative gates remain in JARVIS/Vault."""

    def __init__(
        self,
        parent: tk.Misc,
        gateway: Any,
        *,
        identity: ReviewerIdentity | None = None,
        action_handler: Callable[[str, str, dict[str, Any]], None] | None = None,
    ):
        super().__init__(parent)
        self.gateway = gateway
        self.identity = identity or ReviewerIdentity.unauthenticated()
        self.action_handler = action_handler
        self.title("JARVIS - Memory Review")
        self.geometry("1080x720")
        self.minsize(900, 600)
        self._queue: list[dict[str, Any]] = []
        self._selected_dossier: dict[str, Any] = {}
        self._buttons: dict[str, ttk.Button] = {}
        self._build()
        self.refresh()

    def _build(self) -> None:
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="Memory Review", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Label(toolbar, text=f"Identity: {self.identity.subject or 'none'} / {self.identity.principal.value}").pack(side="left", padx=16)
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side="right")

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        left = ttk.Frame(body, padding=6)
        right = ttk.Frame(body, padding=6)
        body.add(left, weight=2)
        body.add(right, weight=3)

        columns = ("case_id", "risk", "confidence", "priority", "status")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", height=20)
        headings = {"case_id": "Case", "risk": "Risk", "confidence": "Confidence", "priority": "Priority", "status": "Promotable"}
        widths = {"case_id": 170, "risk": 70, "confidence": 85, "priority": 80, "status": 85}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._select_case)

        ttk.Label(right, text="Review dossier", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 6))
        self.details = ScrolledText(right, wrap="word", state="disabled", font=("Consolas", 10))
        self.details.pack(fill="both", expand=True)

        action_bar = ttk.Frame(right, padding=(0, 8, 0, 0))
        action_bar.pack(fill="x")
        for action, label in (
            ("OPEN_REVIEW", "Inspect"),
            ("COLLECT_MORE_EVIDENCE", "More Evidence"),
            ("DEFER", "Defer"),
            ("REQUEST_AUTHORIZED_PROMOTION", "Request Promotion"),
        ):
            button = ttk.Button(action_bar, text=label, command=lambda a=action: self._request_action(a), state="disabled")
            button.pack(side="left", padx=(0, 6))
            self._buttons[action] = button

        self.state = tk.StringVar(value="-")
        ttk.Label(right, textvariable=self.state).pack(anchor="w", pady=(6, 0))

    def refresh(self) -> None:
        try:
            self._queue = self.gateway.learning_review_queue()
        except Exception as exc:
            self._queue = []
            self._selected_dossier = {"error": str(exc)}
            self._show(self._selected_dossier)
            self._update_actions()
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        for item in self._queue:
            self.tree.insert("", "end", iid=str(item.get("case_id")), values=(item.get("case_id", ""), item.get("risk", ""), item.get("confidence_score", ""), item.get("priority", ""), "YES" if item.get("promotable") else "NO"))
        self._selected_dossier = {}
        self.state.set(f"{len(self._queue)} review cases")
        self._update_actions()

    def _select_case(self, _event: object) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        case_id = selected[0]
        try:
            dossier = self.gateway.open_learning_review_session(case_id)
        except Exception as exc:
            dossier = {"error": str(exc), "case_id": case_id}
        self._selected_dossier = dossier
        self._show(dossier)
        self.state.set(f"Selected: {case_id}")
        self._update_actions()

    def _update_actions(self) -> None:
        for button in self._buttons.values():
            button.configure(state="disabled")
        if not self._selected_dossier or self._selected_dossier.get("error"):
            return

        proposed = set(self._selected_dossier.get("proposed_actions") or [])
        if "OPEN_REVIEW" in self._buttons:
            self._buttons["OPEN_REVIEW"].configure(state="normal")
        if not self.identity.can_decide or self.action_handler is None:
            return
        for action in proposed:
            button = self._buttons.get(action)
            if button is not None:
                button.configure(state="normal")
        self.state.set(
            f"{self.state.get()} | {self.identity.principal.value} | "
            f"{'authenticated' if self.identity.authenticated else 'unauthenticated'}"
        )

    def _request_action(self, action: str) -> None:
        if not self.identity.can_decide or self.action_handler is None:
            return
        case = self._selected_dossier.get("case") or {}
        case_id = str(case.get("case_id") or "")
        if not case_id:
            return
        self.action_handler(action, case_id, self._selected_dossier)

    def _show(self, payload: dict[str, Any]) -> None:
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("end", json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        self.details.configure(state="disabled")


def open_reviewer_window(
    parent: tk.Misc,
    gateway: Any,
    *,
    identity: ReviewerIdentity | None = None,
    action_handler: Callable[[str, str, dict[str, Any]], None] | None = None,
) -> ReviewerWindow:
    """Open reviewer UI with explicit identity context."""
    return ReviewerWindow(parent, gateway, identity=identity, action_handler=action_handler)
