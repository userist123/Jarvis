"""Minimal local context bridge to the canonical AI Memory Vault."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Tuple

from jarvis.config import Settings, get_settings


CANONICAL_FILES: Tuple[str, ...] = (
    "AGENTS.md",
    "00_CORE/Identity.md",
    "00_CORE/Rules.md",
    "00_CORE/Memory_Protocol.md",
    "00_CORE/Confidence_Model.md",
    "00_CORE/System_Architecture.md",
    "99_SYSTEM/Classification_Protocol.md",
    "99_SYSTEM/Import_Pipeline.md",
    "99_SYSTEM/Quality_Control.md",
)


class VaultContextLoader:
    """Load only canonical operating-contract notes from the local vault."""

    def __init__(self, vault_root: Path | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.vault_root = Path(vault_root or self.settings.vault_path).expanduser().resolve()

    def available(self) -> bool:
        return self.vault_root.is_dir()

    def iter_existing(self, files: Iterable[str] = CANONICAL_FILES):
        if not self.available():
            return
        for relative in files:
            path = self.vault_root / relative
            if path.is_file():
                yield relative, path

    def load(self, files: Iterable[str] = CANONICAL_FILES, max_chars: int = 24000) -> str:
        """Build a bounded context block for an agent/system prompt."""
        chunks: list[str] = []
        remaining = max(0, max_chars)
        for relative, path in self.iter_existing(files) or ():
            if remaining <= 0:
                break
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            if not text:
                continue
            block = f"\n## {relative}\n{text}\n"
            if len(block) > remaining:
                block = block[:remaining]
            chunks.append(block)
            remaining -= len(block)
        return "".join(chunks).strip()
