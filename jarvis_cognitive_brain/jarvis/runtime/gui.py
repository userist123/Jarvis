from __future__ import annotations

import asyncio
import threading
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText

from jarvis.config import Settings, get_settings
from jarvis.runtime.bootstrap import diagnose
from jarvis.runtime.chat import ChatRuntime


class JarvisApp(tk.Tk):
    """Thin Tkinter desktop shell over the shared JARVIS runtime."""

    def __init__(self, settings: Settings | None = None) -> None:
        super().__init__()
        self.settings = settings or get_settings()
        self.title("JARVIS")
        self.geometry("1100x720")
        self.minsize(820, 560)
        self.configure(padx=12, pady=12)

        self.chat = ChatRuntime(self.settings)
        self.status = tk.StringVar(value="Starting...")
        self.model = tk.StringVar(value=self.settings.ollama_model)
        self.vault = tk.StringVar(value=str(self.settings.vault_path))
        self.evidence = tk.StringVar(value="Evidence: n/a")

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
        body.add(left, weight=3)
        body.add(right, weight=1)

        self.transcript = ScrolledText(left, wrap="word", state="disabled", font=("Consolas", 11))
        self.transcript.pack(fill="both", expand=True)

        composer = ttk.Frame(left)
        composer.pack(fill="x", pady=(10, 0))
        self.input = tk.Text(composer, height=4, wrap="word", font=("Segoe UI", 11))
        self.input.pack(side="left", fill="both", expand=True)
        self.send = ttk.Button(composer, text="Send", command=self._send)
        self.send.pack(side="right", padx=(8, 0), fill="y")

        ttk.Label(right, text="Runtime", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 10))
        self._info_row(right, "Model", self.model)
        self._info_row(right, "Vault", self.vault)
        self._info_row(right, "Grounding", self.evidence)

        ttk.Separator(right).pack(fill="x", pady=12)
        ttk.Label(right, text="Session", font=("Segoe UI", 13, "bold")).pack(anchor="w", pady=(0, 8))
        ttk.Button(right, text="New session", command=self._reset).pack(fill="x")
        ttk.Button(right, text="Refresh status", command=self._refresh_status).pack(fill="x", pady=(6, 0))

    @staticmethod
    def _info_row(parent: ttk.Frame, label: str, variable: tk.StringVar) -> None:
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=f"{label}:").pack(side="left")
        ttk.Label(row, textvariable=variable, wraplength=280).pack(side="right", anchor="e")

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
        threading.Thread(target=self._reply_worker, args=(text,), daemon=True).start()

    def _reply_worker(self, text: str) -> None:
        try:
            answer = asyncio.run(self.chat.reply(text))
        except Exception as exc:
            answer = f"Runtime error: {exc}"
        self.after(0, self._finish_reply, answer)

    def _finish_reply(self, answer: str) -> None:
        self._append("JARVIS", answer)
        self.send.configure(state="normal")
        self.status.set("Ready")

    def _reset(self) -> None:
        self.chat.reset()
        self.transcript.configure(state="normal")
        self.transcript.delete("1.0", "end")
        self.transcript.configure(state="disabled")
        self.evidence.set("Evidence: n/a")

    def _refresh_status(self) -> None:
        def worker() -> None:
            try:
                status = asyncio.run(diagnose(self.settings))
                text = "Ready" if status.ollama_healthy else "Ollama unavailable"
            except Exception as exc:
                text = f"Diagnostics error: {exc}"
            self.after(0, self.status.set, text)

        threading.Thread(target=worker, daemon=True).start()


def main() -> int:
    app = JarvisApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
