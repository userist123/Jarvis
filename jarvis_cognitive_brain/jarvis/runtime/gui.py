from __future__ import annotations

import asyncio
import threading
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from jarvis.config import Settings, get_settings
from jarvis.runtime.bootstrap import diagnose
from jarvis.runtime.chat import ChatRuntime
from jarvis.runtime.reviewer_ui import open_reviewer_window


class JarvisApp(tk.Tk):
    """Thin Tkinter desktop shell over the shared JARVIS runtime."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        self.settings = settings or get_settings()
        self.title("JARVIS")
        self.geometry("1240x780")
        self.minsize(920, 600)
        self.configure(padx=12, pady=12)
        self._reviewer_window: tk.Toplevel | None = None

        self.chat = ChatRuntime(self.settings)
        self.status = tk.StringVar(value="Starting...")
        self.mode = tk.StringVar(value="initializing")
        self.model = tk.StringVar(value=self.settings.ollama_model)
        self.vault = tk.StringVar(value=str(self.settings.vault_path))
        self.executive = tk.StringVar(value="checking...")
        self.agent = tk.StringVar(value="not routed")
        self.agent_score = tk.StringVar(value="-")
        self.evidence = tk.StringVar(value="n/a")
        self.memory_count = tk.StringVar(value="0")
        self.memory_ids = tk.StringVar(value="-")
        self.context_chars = tk.StringVar(value="0")
        self.tool_state = tk.StringVar(value="policy-gated")
        self.plan_state = tk.StringVar(value="idle")
        self.session = tk.StringVar(value=self.chat.session_id)

        self._build_ui()
        self.bind("<Control-Return>", lambda _event: self._send())
        self.after(100, self._refresh_status)

    def _build_ui(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 10))
        ttk.Label(header, text="JARVIS", font=("Segoe UI", 20, "bold")).pack(side="left")
        ttk.Label(header, textvariable=self.status).pack(side="right")

        body = ttk.Panedwindow(self, orient="horizontal")
        body.pack(fill="both", expand=True)

        left = ttk.Frame(body, padding=8)
        right = ttk.Frame(body, padding=8)
        body.add(left, weight=4)
        body.add(right, weight=2)

        self.transcript = ScrolledText(left, wrap="word", state="disabled", font=("Consolas", 11))
        self.transcript.pack(fill="both", expand=True)

        composer = ttk.Frame(left)
        composer.pack(fill="x", pady=(10, 0))
        self.input = tk.Text(composer, height=4, wrap="word", font=("Segoe UI", 11))
        self.input.pack(side="left", fill="both", expand=True)
        self.send = ttk.Button(composer, text="Send", command=self._send)
        self.send.pack(side="right", padx=(8, 0), fill="y")

        ttk.Label(right, text="Cognitive Dashboard", font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 10))
        self._info_row(right, "Status", self.status)
        self._info_row(right, "Mode", self.mode)
        self._info_row(right, "Model", self.model)
        self._info_row(right, "Vault", self.vault)
        self._info_row(right, "Executive", self.executive)
        self._info_row(right, "Agent", self.agent)
        self._info_row(right, "Agent score", self.agent_score)

        ttk.Separator(right).pack(fill="x", pady=10)
        ttk.Label(right, text="Grounding", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))
        self._info_row(right, "Evidence", self.evidence)
        self._info_row(right, "Memory count", self.memory_count)
        self._info_row(right, "Context chars", self.context_chars)
        self._info_row(right, "Memory IDs", self.memory_ids)

        ttk.Separator(right).pack(fill="x", pady=10)
        ttk.Label(right, text="Execution", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 8))
        self._info_row(right, "Plan", self.plan_state)
        self._info_row(right, "Tools", self.tool_state)
        self._info_row(right, "Session", self.session)

        ttk.Separator(right).pack(fill="x", pady=12)
        ttk.Button(right, text="Open Memory Review", command=self._open_reviewer).pack(fill="x")
        ttk.Button(right, text="New session", command=self._reset).pack(fill="x", pady=(6, 0))
        ttk.Button(right, text="Refresh status", command=self._refresh_status).pack(fill="x", pady=(6, 0))

    @staticmethod
    def _info_row(parent: ttk.Frame, label: str, variable: tk.StringVar) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=f"{label}:").pack(side="left")
        ttk.Label(row, textvariable=variable, wraplength=300, justify="right").pack(side="right", anchor="e")

    def _append(self, speaker: str, text: str) -> None:
        self.transcript.configure(state="normal")
        self.transcript.insert("end", f"{speaker}: {text}\n\n")
        self.transcript.see("end")
        self.transcript.configure(state="disabled")

    def _send(self) -> None:
        text = self.input.get("1.0", "end").strip()
        if not text:
            return
        self.input.delete("1.0", "end")
        self._append("You", text)
        self.send.configure(state="disabled")
        self.status.set("Thinking...")
        threading.Thread(target=self._reply_worker, args=(text,), daemon=True).start()

    @staticmethod
    def _extract_answer(result: object) -> str:
        if isinstance(result, dict):
            for key in ("answer", "response", "content", "message"):
                value = result.get(key)
                if value:
                    return str(value)
            return str(result)
        return str(result)

    def _reply_worker(self, text: str) -> None:
        try:
            gateway = self.chat.gateway
            routes, council = gateway.route_agents(text)
            vault_hits = gateway.search_vault(text, limit=8)
            top = routes[0] if routes else None

            if gateway.executive.available:
                result = gateway.process_intent(text)
                answer = self._extract_answer(result)
                mode = "canonical-executive"
            else:
                answer = asyncio.run(self.chat.reply(text))
                mode = "local-chat-fallback"

            metadata = {
                "mode": mode,
                "agent": getattr(top, "agent_id", None) if top else None,
                "agent_score": getattr(top, "score", None) if top else None,
                "memory_ids": [str(item.get("id")) for item in vault_hits if item.get("id")],
                "memory_count": len(vault_hits),
                "context_chars": sum(len(str(item.get("content", ""))) for item in vault_hits),
                "council": getattr(council, "mode", None),
            }
        except Exception as exc:
            answer = f"Runtime error: {exc}"
            metadata = {"mode": "error", "error": str(exc)}
        self.after(0, self._finish_reply, answer, metadata)

    def _finish_reply(self, answer: str, metadata: dict) -> None:
        self._append("JARVIS", answer)
        self.mode.set(str(metadata.get("mode", "unknown")))
        if metadata.get("error"):
            self.executive.set(f"error: {metadata['error']}")
        else:
            self.agent.set(str(metadata.get("agent") or "not routed"))
            score = metadata.get("agent_score")
            self.agent_score.set(f"{score:.3f}" if isinstance(score, (int, float)) else "-")
            ids = metadata.get("memory_ids", [])
            self.memory_count.set(str(metadata.get("memory_count", 0)))
            self.memory_ids.set(", ".join(ids[:6]) if ids else "-")
            self.context_chars.set(str(metadata.get("context_chars", 0)))
            self.evidence.set("retrieved preview" if ids else "none retrieved")
            self.plan_state.set(str(metadata.get("council") or "single-agent"))
        self.send.configure(state="normal")
        self.status.set("Ready")

    def _open_reviewer(self) -> None:
        if self._reviewer_window is not None and self._reviewer_window.winfo_exists():
            self._reviewer_window.lift()
            self._reviewer_window.focus_force()
            return
        identity = self.chat.gateway.current_reviewer_identity()
        self._reviewer_window = open_reviewer_window(self, self.chat.gateway, identity=identity)
        self._reviewer_window.protocol("WM_DELETE_WINDOW", self._close_reviewer)

    def _close_reviewer(self) -> None:
        if self._reviewer_window is not None:
            self._reviewer_window.destroy()
        self._reviewer_window = None

    def _reset(self) -> None:
        self.chat.reset()
        self.session.set(self.chat.session_id)
        self.transcript.configure(state="normal")
        self.transcript.delete("1.0", "end")
        self.transcript.configure(state="disabled")
        self.mode.set("ready")
        self.evidence.set("n/a")
        self.agent.set("not routed")
        self.agent_score.set("-")
        self.memory_count.set("0")
        self.memory_ids.set("-")
        self.context_chars.set("0")
        self.plan_state.set("idle")

    def _refresh_status(self) -> None:
        def worker() -> None:
            try:
                status = asyncio.run(diagnose(self.settings))
                runtime_text = "Ready" if status.ollama_healthy else "Ollama unavailable"
                exec_text = "available" if status.executive_available else status.executive_reason
            except Exception as exc:
                runtime_text = f"Diagnostics error: {exc}"
                exec_text = "unknown"
            self.after(0, self._apply_status, runtime_text, exec_text)

        threading.Thread(target=worker, daemon=True).start()

    def _apply_status(self, runtime_text: str, executive_text: str) -> None:
        self.status.set(runtime_text)
        self.executive.set(executive_text)


def main() -> int:
    app = JarvisApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
