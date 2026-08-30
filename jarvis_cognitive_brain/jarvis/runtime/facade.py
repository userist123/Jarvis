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
from jarvis.agents.agent_council import CouncilPlan

# Mirrors the Council-wide agent cap used in the AI Memory Vault
# (Council_Selection_Boundary.MAX_AGENTS_PER_COUNCIL): a primary agent plus at
# most this many additional reviewers may be part of one Council decision.
MAX_COUNCIL_AGENTS = 3


class CouncilBudgetExceededError(RuntimeError):
    """Raised when a CouncilPlan requires more agents than the runtime allows.

    Mirrors the fail-closed contract used by
    Council_Selection_Boundary.enforce_council_boundary() in the memory
    vault: a Council plan that exceeds the agent budget must abort BEFORE the
    Executive is invoked, not be silently downgraded to a single-agent call.
    """


@dataclass(frozen=True)
class RuntimeTurn:
    mode: str
    intent: str
    result: Dict[str, Any]
    routes: tuple[str, ...] = ()
    council: Optional[CouncilPlan] = None


class RuntimeFacade:
    """One execution boundary shared by CLI and GUI."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        gateway: Optional[CognitiveGateway] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.gateway = gateway or CognitiveGateway(settings=self.settings)

    def route(self, intent: str) -> tuple[list[str], CouncilPlan]:
        """Rank candidate agents and decide single-agent vs Council mode.

        Bug fix: AgentRoute.agent (jarvis.agents.agent_router.AgentRoute) is a
        plain str -- the agent's name -- not an object with a `.name`
        attribute. The previous implementation called `route.agent.name`,
        which raised AttributeError as soon as any agent actually matched.
        `route.agent` is used directly now.
        """
        routes, council = self.gateway.route_agents(intent)
        return [route.agent for route in routes], council

    def execute(self, intent: str) -> RuntimeTurn:
        """Execute an intent through the canonical Executive when available.

        Fail-closed Council contract (previously missing entirely -- the
        CouncilPlan computed by route() was discarded via `_council` and
        never enforced or surfaced):
          1. The CouncilPlan is attached to the returned RuntimeTurn so
             callers can see whether single-agent or Council-level review was
             required.
          2. If the plan requires more than MAX_COUNCIL_AGENTS agents
             (primary + reviewers), this raises CouncilBudgetExceededError
             BEFORE the Executive is invoked -- no execution happens on an
             over-budget Council decision.
          3. The underlying Executive (`gateway.process_intent`) only ever
             performs one undifferentiated call; it has no per-agent
             execution path yet. When council.mode == "council", the turn's
             mode is marked "canonical-executive-council-required" instead of
             plain "canonical-executive", so nothing pretends independent
             multi-agent reasoning happened when only one canonical call was
             actually made.
        """
        routes, council = self.route(intent)

        agent_count = 1 + len(council.reviewers) if council.primary else 0
        if council.mode == "council" and agent_count > MAX_COUNCIL_AGENTS:
            raise CouncilBudgetExceededError(
                f"Council plan requires {agent_count} agents "
                f"(primary + {len(council.reviewers)} reviewers) > {MAX_COUNCIL_AGENTS}"
            )

        if self.gateway.executive.available:
            result = self.gateway.process_intent(intent)
            mode = (
                "canonical-executive-council-required"
                if council.mode == "council"
                else "canonical-executive"
            )
            return RuntimeTurn(
                mode=mode,
                intent=intent,
                result=dict(result),
                routes=tuple(routes),
                council=council,
            )

        return RuntimeTurn(
            mode="local-chat-fallback",
            intent=intent,
            result={
                "status": "not_executed",
                "reason": self.gateway.executive.reason,
            },
            routes=tuple(routes),
            council=council,
        )
