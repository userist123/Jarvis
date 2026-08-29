"""Adapter for the canonical AI Memory Vault cognitive Executive.

JARVIS consumes the Vault Executive through a narrow protocol instead of
reimplementing Activation, Recall, Working Memory, Planning and Reflection.
The adapter is fail-closed when the native Vault package is unavailable.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Any, Optional, Protocol

from jarvis.memory.vault_bridge import VaultBridge


class ExecutiveBackend(Protocol):
    def process_intent(self, principal: Any, intent_text: str) -> dict[str, Any]: ...


class NativeExecutiveBackend:
    """Load the canonical Vault Executive without copying its implementation."""

    def __init__(self, vault_root: Path) -> None:
        if str(vault_root) not in sys.path:
            sys.path.insert(0, str(vault_root))
        module = importlib.import_module("cognitive_core.executive")
        self._principal_module = importlib.import_module("memory_controller.authorizer")
        executive_cls = getattr(module, "Executive")
        self.executive = executive_cls()

    def process_intent(self, principal: Any, intent_text: str) -> dict[str, Any]:
        return dict(self.executive.process_intent(principal, intent_text))


class ExecutiveAdapter:
    """Stable JARVIS entry point for the canonical cognitive Executive."""

    def __init__(self, vault_root: str | Path, backend: Optional[ExecutiveBackend] = None) -> None:
        self.root = Path(vault_root).expanduser().resolve()
        self._backend = backend
        self._reason = "injected backend"
        if backend is None:
            self._backend, self._reason = self._discover()
        self.vault = VaultBridge(self.root)

    def _discover(self) -> tuple[Optional[ExecutiveBackend], str]:
        if not self.root.is_dir():
            return None, "vault root is not available"
        if not (self.root / "cognitive_core" / "executive.py").is_file():
            return None, "canonical Executive is not present"
        try:
            return NativeExecutiveBackend(self.root), "native Executive loaded"
        except Exception as exc:
            return None, f"native Executive unavailable: {exc.__class__.__name__}"

    @property
    def available(self) -> bool:
        return self._backend is not None

    @property
    def reason(self) -> str:
        return self._reason

    def process_intent(self, principal: Any, intent_text: str) -> dict[str, Any]:
        if self._backend is None:
            raise RuntimeError(f"Executive backend unavailable: {self._reason}")
        return self._backend.process_intent(principal, intent_text)

    def process_as_ai_agent(self, intent_text: str) -> dict[str, Any]:
        """Run through the Vault Executive as the AI_AGENT principal."""
        if self._backend is None:
            raise RuntimeError(f"Executive backend unavailable: {self._reason}")
        from memory_controller.authorizer import Principal

        return self._backend.process_intent(Principal.AI_AGENT, intent_text)
