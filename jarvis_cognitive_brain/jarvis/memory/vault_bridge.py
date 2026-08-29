"""Guarded bridge between JARVIS and an optional native AI Memory Vault runtime.

The bridge deliberately exposes a narrow interface. JARVIS can consume the
Vault's richer MemoryController/Recall/Activation stack when it is importable,
while retaining the local Markdown/SQLite implementation as a safe fallback.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Protocol


class VaultBackend(Protocol):
    def search_memory(self, query: str, limit: int = 20) -> list[dict[str, Any]]: ...

    def related_memory(self, note_id: str, limit: int = 20) -> list[dict[str, Any]]: ...

    def propose_memory(self, note: dict[str, Any]) -> Any: ...


@dataclass(frozen=True)
class VaultBridgeStatus:
    available: bool
    backend: str
    root: str
    reason: str = ""


class VaultBridge:
    """Fail-closed bridge for optional native Vault integration."""

    def __init__(self, vault_root: str | Path, backend: Optional[VaultBackend] = None) -> None:
        self.root = Path(vault_root).expanduser().resolve()
        self._backend = backend
        self._status_reason = "injected backend"
        if backend is None:
            self._backend, self._status_reason = self._discover_backend()

    def _discover_backend(self) -> tuple[Optional[VaultBackend], str]:
        if not self.root.is_dir():
            return None, "vault root is not available"
        package_root = self.root / "memory_controller"
        cognitive_root = self.root / "cognitive_core"
        if not (package_root.is_dir() and cognitive_root.is_dir()):
            return None, "native Vault modules are not present at the configured root"
        return None, "native modules detected but adapter is not installed"

    @property
    def available(self) -> bool:
        return self._backend is not None

    @property
    def status(self) -> VaultBridgeStatus:
        return VaultBridgeStatus(
            available=self.available,
            backend=type(self._backend).__name__ if self._backend else "fallback",
            root=str(self.root),
            reason=self._status_reason,
        )

    def search_memory(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        if not self._backend:
            return []
        return list(self._backend.search_memory(query, limit=limit))

    def related_memory(self, note_id: str, limit: int = 20) -> list[dict[str, Any]]:
        if not self._backend:
            return []
        return list(self._backend.related_memory(note_id, limit=limit))

    def propose_memory(self, note: dict[str, Any]) -> Any:
        if not self._backend:
            return None
        return self._backend.propose_memory(dict(note))
