"""Tkinter unified governance center backed by read-only governance projections."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any


class GovernanceCenterWindow(tk.Toplevel):
    """Read-only consolidated view of learning, conflict and intelligence governance."""

    def __init__(self, parent: tk.Misc, gateway: Any):
        super().__init__(parent)
        self.gateway = gateway
        self.title("JARVIS - Governance Center")
        self.geometry("1120x760")
        self.minsize(920, 640)
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
        self.intelligence = tk.StringVar(value="Intelligence: -")
        self.pending = tk.StringVar(value="Pending: -")
        for variable in (self.identity, self.learning, self.conflicts, self.intelligence, self.pending):
            ttk.Label(summary, textvariable=variable).pack(anchor="w", pady=2)

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        left = ttk.Frame(body, padding=6)
        right = ttk.Frame(body, padding=6)
        body.add(left, weight=2)
        body.add(right, weight=3)

        ttk.Label(left, text="Pending actions", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 6))
        self.tree = ttk.Treeview(left, columns=("case_id", "state", "mutation"), show="headings", height=20)
        for column, heading, width in (("case_id", "Case", 190), ("state", "State", 150), ("mutation", "Mutation", 90)):
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._select_pending)

        ttk.Label(right, text="Governance snapshot", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 6))
        self.details = ScrolledText(right, wrap="word", state="disabled", font=("Consolas", 10))
        self.details.pack(fill="both", expand=True)

        self.status = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status).pack(fill="x", padx=8, pady=(0, 8))
        self._snapshot: dict[str, Any] = {}

    def refresh(self) -> None:
        try:
            self._snapshot = self.gateway.governance_center()
        except Exception as exc:
            self._snapshot = {"error": str(exc)}
            self._show(self._snapshot)
            self.status.set(f"Error: {exc}")
            return

        identity = self._snapshot.get("identity") or {}
        learning = self._snapshot.get("learning") or {}
        conflicts = self._snapshot.get("conflicts") or {}
        intelligence = self._snapshot.get("intelligence") or {}
        pending = self._snapshot.get("pending_actions") or []
        self.identity.set(f"Identity: {identity.get('subject') or 'none'} / {identity.get('principal', 'UNAUTHENTICATED')}")
        self.learning.set(f"Learning cases: {learning.get('total_cases', 0)} | promotable: {learning.get('promotable', 0)} | high-risk: {learning.get('high_risk', 0)}")
        self.conflicts.set(f"Conflict cases: {conflicts.get('total_cases', 0)}")
        self.intelligence.set(f"Memory signals: {intelligence.get('total', 0)} | routes: {intelligence.get('by_route', {})}")
        self.pending.set(f"Pending actions: {len(pending)}")
        for item in self.tree.get_children():
            self.tree.delete(item)
        for index, item in enumerate(pending):
            iid = f"{item.get('kind', 'case')}:{item.get('case_id', index)}"
            self.tree.insert("", "end", iid=iid, values=(item.get("case_id", ""), item.get("state", ""), "YES" if item.get("can_apply_mutation") else "NO"))
        self._show(self._snapshot)
        self.status.set("Read-only governance snapshot refreshed")

    def _select_pending(self, _event: object) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        iid = selected[0]
        case_id = iid.split(":", 1)[-1]
        for item in self._snapshot.get("pending_actions") or []:
            if str(item.get("case_id")) == case_id:
                self._show(item)
                self.status.set(f"Selected: {case_id}")
                return

    def _show(self, payload: dict[str, Any]) -> None:
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("end", json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        self.details.configure(state="disabled")


def open_governance_center(parent: tk.Misc, gateway: Any) -> GovernanceCenterWindow:
    return GovernanceCenterWindow(parent, gateway)
