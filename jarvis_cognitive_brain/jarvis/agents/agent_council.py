"""Deterministic agent-council orchestration policy."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from jarvis.agents.agent_router import AgentRoute


@dataclass(frozen=True)
class CouncilPlan:
    mode: str
    primary: str | None
    reviewers: tuple[str, ...]
    reason: str


class AgentCouncil:
    """Choose single-agent or council execution from task complexity and risk."""

    def __init__(self, *, complexity_threshold: int = 2, risky_capabilities: Iterable[str] = ()) -> None:
        self.complexity_threshold = max(1, complexity_threshold)
        self.risky_capabilities = {str(c).casefold() for c in risky_capabilities}

    def plan(
        self,
        routes: list[AgentRoute],
        required_capabilities: Iterable[str] = (),
        *,
        complexity: int = 1,
        require_review: bool = False,
    ) -> CouncilPlan:
        required = {str(c).casefold() for c in required_capabilities}
        risky = bool(required & self.risky_capabilities)
        use_council = require_review or risky or complexity >= self.complexity_threshold
        primary = routes[0].agent if routes else None
        reviewers = tuple(route.agent for route in routes[1:3]) if use_council else ()

        if not primary:
            return CouncilPlan("unrouted", None, (), "No eligible agent matched the task.")
        if use_council:
            return CouncilPlan("council", primary, reviewers, "Complexity, risk, or explicit review requires multi-agent validation.")
        return CouncilPlan("single", primary, (), "Task is suitable for a single routed agent.")
