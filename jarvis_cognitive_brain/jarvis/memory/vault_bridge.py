"""Guarded bridge between JARVIS and the canonical AI Memory Vault runtime.

The native adapter is optional and discovered only when the configured Vault
contains the real ``memory_controller`` package. JARVIS never touches the
Vault storage engine directly; reads/writes go through MemoryController so
its authorization, validation and audit rules remain in force.
"""

from __future__ import annotations

import importlib
import sys
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


class NativeMemoryControllerBackend:
    """Adapter exposing only authorized MemoryController operations."""

    def __init__(self, vault_root: Path) -> None:
        if str(vault_root) not in sys.path:
            sys.path.insert(0, str(vault_root))

        controller_module = importlib.import_module("memory_controller.controller")
        authorizer_module = importlib.import_module("memory_controller.authorizer")
        storage_module = importlib.import_module("memory_controller.storage.file_engine")

        storage = storage_module.FileStorageEngine(str(vault_root))
        self.controller = controller_module.MemoryController(storage)
        self.principal = authorizer_module.Principal.AI_AGENT

    def search_memory(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        # Controller.search provides the complete native retrieval pipeline.
        pack = self.controller.search(self.principal, query, page_size=max(1, min(limit, 100)))
        return list(pack.get("results", pack.get("items", [])))

    def related_memory(self, note_id: str, limit: int = 20) -> list[dict[str, Any]]:
        note = self.controller.cognitive_read(self.principal, note_id)
        return list(note.get("results", note.get("items", [])))[:limit]

    def propose_memory(self, note: dict[str, Any]) -> Any:
        return self.controller.propose(self.principal, dict(note))


class VaultBridge:
    """Fail-closed bridge for optional native Vault integration."""

    def __init__(self, vault_root: str | Path, backend: Optional[VaultBackend] = None, *, enable_native: bool = True) -> None:
        self.root = Path(vault_root).expanduser().resolve()
        self._backend = backend
        self._status_reason = "injected backend"
        if backend is None and enable_native:
            self._backend, self._status_reason = self._discover_backend()
        elif backend is None:
            self._status_reason = "native bridge disabled"

    def _discover_backend(self) -> tuple[Optional[VaultBackend], str]:
        if not self.root.is_dir():
            return None, "vault root is not available"
        if not (self.root / "memory_controller" / "controller.py").is_file():
            return None, "native MemoryController is not present"
        try:
            return NativeMemoryControllerBackend(self.root), "native MemoryController backend loaded"
        except Exception as exc:
            return None, f"native backend unavailable: {exc.__class__.__name__}"

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
