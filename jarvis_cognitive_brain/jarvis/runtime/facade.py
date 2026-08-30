"""Single orchestration facade for CLI and desktop JARVIS runtimes.

The facade keeps UI/runtime callers independent from the internal cognitive
components. It prefers the canonical Vault Executive and exposes a controlled
local-chat fallback when that executive is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from jarvis.config import Settings, get_settings
from jarvis.core.cognitive_gateway import CognitiveGateway


@dataclass(frozen=True)
class RuntimeTurn:
    mode: str
    intent: str
    result: Dict[str, Any]
    routes: tuple[str, ...] = ()


class RuntimeFacade:
    """One execution boundary shared by CLI and GUI."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        gateway: Optional[CognitiveGateway] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.gateway = gateway or CognitiveGateway(settings=self.settings)

    def route(self, intent: str) -> tuple[list[str], Any]:
        routes, council = self.gateway.route_agents(intent)
        return [route.agent.name for route in routes], council

    def execute(self, intent: str) -> RuntimeTurn:
        """Execute an intent through the canonical Executive when available."""
        routes, _council = self.route(intent)
        if self.gateway.executive.available:
            result = self.gateway.process_intent(intent)
            return RuntimeTurn(
                mode="canonical-executive",
                intent=intent,
                result=dict(result),
                routes=tuple(routes),
            )

        return RuntimeTurn(
            mode="local-chat-fallback",
            intent=intent,
            result={
                "status": "not_executed",
                "reason": self.gateway.executive.reason,
            },
            routes=tuple(routes),
        )
