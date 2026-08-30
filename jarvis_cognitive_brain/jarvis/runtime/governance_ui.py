"""Tkinter unified governance center backed by read-only governance projections."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any, Callable


class GovernanceCenterWindow(tk.Toplevel):
    """Read-only consolidated view of learning and conflict governance."""

    def __init__(
        self,
        parent: tk.Misc,
        gateway: Any,
        *,
        open_learning: Callable[[str], None] | None = None,
        open_conflict: Callable[[str], None] | None = None,
    ):
        super().__init__(parent)
        self.gateway = gateway
        self.open_learning = open_learning
        self.open_conflict = open_conflict
        self.title("JARVIS - Governance Center")
        self.geometry("1160x780")
        self.minsize(940, 650)
        self._snapshot: dict[str, Any] = {}
        self._build()
        self.refresh()

    def _build(self) -> None:
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="Governance Center", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side="right")

        summary = ttk.Frame(self, padding=(8, 0, 8, 8))
        summary.pack(fill="x")
        self.identity = tk.StringVar(value="Identity: -")
        self.learning = tk.StringVar(value="Learning: -")
        self.conflicts = tk.StringVar(value="Conflicts: -")
        self.pending = tk.StringVar(value="Pending: -")
        for variable in (self.identity, self.learning, self.conflicts, self.pending):
            ttk.Label(summary, textvariable=variable).pack(anchor="w", pady=2)

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        left = ttk.Frame(body, padding=6)
        right = ttk.Frame(body, padding=6)
        body.add(left, weight=2)
        body.add(right, weight=3)

        ttk.Label(left, text="Pending review items", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 6))
        self.tree = ttk.Treeview(
            left,
            columns=("kind", "case_id", "state", "risk", "confidence", "mutation"),
            show="headings",
            height=20,
        )
        headings = {
            "kind": "Type",
            "case_id": "Case",
            "state": "State",
            "risk": "Risk",
            "confidence": "Confidence",
            "mutation": "Mutation",
        }
        widths = {"kind": 80, "case_id": 175, "state": 145, "risk": 70, "confidence": 85, "mutation": 80}
        for column in self.tree["columns"]:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._select_pending)

        action_bar = ttk.Frame(left, padding=(0, 8, 0, 0))
        action_bar.pack(fill="x")
        self.open_button = ttk.Button(action_bar, text="Open Selected", command=self._open_selected, state="disabled")
        self.open_button.pack(fill="x")

        ttk.Label(right, text="Governance snapshot", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 6))
        self.details = ScrolledText(right, wrap="word", state="disabled", font=("Consolas", 10))
        self.details.pack(fill="both", expand=True)

        self.status = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status).pack(fill="x", padx=8, pady=(0, 8))

    def refresh(self) -> None:
        try:
            self._snapshot = self.gateway.governance_center()
        except Exception as exc:
            self._snapshot = {"error": str(exc)}
            self._show(self._snapshot)
            self.status.set(f"Error: {exc}")
            self.open_button.configure(state="disabled")
            return

        identity = self._snapshot.get("identity") or {}
        learning = self._snapshot.get("learning") or {}
        conflicts = self._snapshot.get("conflicts") or {}
        pending = self._snapshot.get("pending_actions") or []
        self.identity.set(
            f"Identity: {identity.get('subject') or 'none'} / "
            f"{identity.get('principal', 'UNAUTHENTICATED')} / "
            f"{'authenticated' if identity.get('authenticated') else 'unauthenticated'}"
        )
        self.learning.set(
            f"Learning cases: {learning.get('total_cases', 0)} | "
            f"promotable: {learning.get('promotable', 0)} | "
            f"high-risk: {learning.get('high_risk', 0)}"
        )
        self.conflicts.set(f"Conflict cases: {conflicts.get('total_cases', 0)}")
        self.pending.set(f"Pending items: {len(pending)}")
        for item in self.tree.get_children():
            self.tree.delete(item)
        for index, item in enumerate(pending):
            self.tree.insert(
                "",
                "end",
                iid=f"item-{index}",
                values=(
                    item.get("kind", ""),
                    item.get("case_id", ""),
                    item.get("state", ""),
                    item.get("risk", ""),
                    item.get("confidence", ""),
                    "YES" if item.get("can_apply_mutation") else "NO",
                ),
            )
        self._show(self._snapshot)
        self.status.set("Read-only governance snapshot refreshed")
        self.open_button.configure(state="disabled")

    def _select_pending(self, _event: object) -> None:
        selected = self.tree.selection()
        if not selected:
            self.open_button.configure(state="disabled")
            return
        index = int(selected[0].split("-", 1)[1])
        pending = self._snapshot.get("pending_actions") or []
        if index >= len(pending):
            self.open_button.configure(state="disabled")
            return
        self._show(pending[index])
        self.status.set(f"Selected: {pending[index].get('case_id', '-')}")
        self.open_button.configure(state="normal")

    def _open_selected(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        index = int(selected[0].split("-", 1)[1])
        pending = self._snapshot.get("pending_actions") or []
        if index >= len(pending):
            return
        item = pending[index]
        case_id = str(item.get("case_id") or "")
        kind = str(item.get("kind") or "")
        if kind == "learning" and self.open_learning:
            self.open_learning(case_id)
        elif kind == "conflict" and self.open_conflict:
            self.open_conflict(case_id)

    def _show(self, payload: dict[str, Any]) -> None:
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("end", json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        self.details.configure(state="disabled")


def open_governance_center(
    parent: tk.Misc,
    gateway: Any,
    *,
    open_learning: Callable[[str], None] | None = None,
    open_conflict: Callable[[str], None] | None = None,
) -> GovernanceCenterWindow:
    return GovernanceCenterWindow(
        parent,
        gateway,
        open_learning=open_learning,
        open_conflict=open_conflict,
    )
