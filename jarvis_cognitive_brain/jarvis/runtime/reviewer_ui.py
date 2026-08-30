"""Tkinter reviewer window backed by the read-only JARVIS review contracts."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any, Callable


class ReviewerWindow(tk.Toplevel):
    """Read-only review UI. Mutations are intentionally not exposed here."""

    def __init__(self, parent: tk.Misc, gateway: Any):
        super().__init__(parent)
        self.gateway = gateway
        self.title("JARVIS - Memory Review")
        self.geometry("1080x680")
        self.minsize(900, 560)
        self._queue: list[dict[str, Any]] = []
        self._build()
        self.refresh()

    def _build(self) -> None:
        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="Memory Review", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Button(toolbar, text="Refresh", command=self.refresh).pack(side="right")

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        left = ttk.Frame(body, padding=6)
        right = ttk.Frame(body, padding=6)
        body.add(left, weight=2)
        body.add(right, weight=3)

        columns = ("case_id", "risk", "confidence", "priority", "status")
        self.tree = ttk.Treeview(left, columns=columns, show="headings", height=20)
        headings = {
            "case_id": "Case",
            "risk": "Risk",
            "confidence": "Confidence",
            "priority": "Priority",
            "status": "Promotable",
        }
        widths = {"case_id": 170, "risk": 70, "confidence": 85, "priority": 80, "status": 85}
        for column in columns:
            self.tree.heading(column, text=headings[column])
            self.tree.column(column, width=widths[column], anchor="center")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._select_case)

        ttk.Label(right, text="Review dossier", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 6))
        self.details = ScrolledText(right, wrap="word", state="disabled", font=("Consolas", 10))
        self.details.pack(fill="both", expand=True)

        self.state = tk.StringVar(value="-")
        ttk.Label(right, textvariable=self.state).pack(anchor="w", pady=(6, 0))

    def refresh(self) -> None:
        try:
            self._queue = self.gateway.learning_review_queue()
        except Exception as exc:
            self._queue = []
            self._show({"error": str(exc)})
            return
        for item in self.tree.get_children():
            self.tree.delete(item)
        for item in self._queue:
            self.tree.insert(
                "",
                "end",
                iid=str(item.get("case_id")),
                values=(
                    item.get("case_id", ""),
                    item.get("risk", ""),
                    item.get("confidence_score", ""),
                    item.get("priority", ""),
                    "YES" if item.get("promotable") else "NO",
                ),
            )
        self.state.set(f"{len(self._queue)} review cases")

    def _select_case(self, _event: object) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        case_id = selected[0]
        try:
            dossier = self.gateway.open_learning_review_session(case_id)
        except Exception as exc:
            dossier = {"error": str(exc), "case_id": case_id}
        self._show(dossier)

    def _show(self, payload: dict[str, Any]) -> None:
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("end", json.dumps(payload, indent=2, ensure_ascii=False, default=str))
        self.details.configure(state="disabled")


def open_reviewer_window(parent: tk.Misc, gateway: Any) -> ReviewerWindow:
    """Open a reviewer window and return it to the caller for lifecycle control."""
    return ReviewerWindow(parent, gateway)
