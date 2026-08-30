from __future__ import annotations

from pathlib import Path

import pytest

from jarvis.config import Settings
from jarvis.agents.agent_router import AgentRoute
from jarvis.agents.agent_council import CouncilPlan
from jarvis.runtime.facade import RuntimeFacade, CouncilBudgetExceededError, MAX_COUNCIL_AGENTS


class FakeExecutive:
    available = True
    reason = "native Executive loaded"

    def process_as_ai_agent(self, intent_text: str):
        return {"status": "success", "intent": intent_text}


def _route(name: str) -> AgentRoute:
    # AgentRoute.agent is a plain str (see jarvis.agents.agent_router). This
    # fixture intentionally matches that real contract -- the previous
    # version of this test used a fake `route.agent` object with a `.name`
    # attribute, which matched the buggy `route.agent.name` implementation
    # instead of the real dataclass, and therefore never caught the
    # AttributeError that real usage would raise.
    return AgentRoute(agent=name, score=1.0, matched_capabilities=(), matched_keywords=(), reason="test")


class FakeGateway:
    def __init__(self, executive, routes=None, council=None):
        self.executive = executive
        self._routes = routes if routes is not None else [_route("test-agent")]
        self._council = council if council is not None else CouncilPlan("single", "test-agent", (), "test")

    def route_agents(self, task):
        return self._routes, self._council

    def process_intent(self, intent_text):
        return self.executive.process_as_ai_agent(intent_text)


def test_facade_prefers_canonical_executive(tmp_path: Path):
    settings = Settings(vault_path=tmp_path / "vault")
    facade = RuntimeFacade(settings=settings, gateway=FakeGateway(FakeExecutive()))
    result = facade.execute("inspect vault")
    assert result.mode == "canonical-executive"
    assert result.routes == ("test-agent",)
    assert result.result["status"] == "success"
    assert result.council.mode == "single"


def test_facade_is_explicit_when_executive_unavailable(tmp_path: Path):
    settings = Settings(vault_path=tmp_path / "vault")
    unavailable = type("E", (), {"available": False, "reason": "vault missing"})()
    facade = RuntimeFacade(settings=settings, gateway=FakeGateway(unavailable))
    result = facade.execute("inspect vault")
    assert result.mode == "local-chat-fallback"
    assert result.result["status"] == "not_executed"
    assert result.result["reason"] == "vault missing"


def test_route_does_not_crash_when_multiple_agents_match(tmp_path: Path):
    # Regression test for the `route.agent.name` bug: AgentRoute.agent is a
    # plain str, so calling `.name` on it raised AttributeError whenever any
    # agent matched. This is the exact multi-agent case that must now work.
    settings = Settings(vault_path=tmp_path / "vault")
    routes = [_route("secops_auditor"), _route("backend_systems_engineer")]
    council = CouncilPlan("single", "secops_auditor", (), "test")
    facade = RuntimeFacade(settings=settings, gateway=FakeGateway(FakeExecutive(), routes=routes, council=council))

    names, plan = facade.route("audit the logs")

    assert names == ["secops_auditor", "backend_systems_engineer"]
    assert plan is council


def test_council_mode_within_budget_executes_and_marks_mode(tmp_path: Path):
    settings = Settings(vault_path=tmp_path / "vault")
    routes = [_route("a"), _route("b"), _route("c")]
    council = CouncilPlan("council", "a", ("b", "c"), "risky capability")
    facade = RuntimeFacade(settings=settings, gateway=FakeGateway(FakeExecutive(), routes=routes, council=council))

    turn = facade.execute("deploy to production")

    assert turn.mode == "canonical-executive-council-required"
    assert turn.council.reviewers == ("b", "c")


def test_council_mode_over_budget_fails_closed_before_executive_call(tmp_path: Path):
    settings = Settings(vault_path=tmp_path / "vault")
    routes = [_route(f"agent_{i}") for i in range(5)]
    council = CouncilPlan("council", "agent_0", ("agent_1", "agent_2", "agent_3"), "over budget")

    class TrackingExecutive(FakeExecutive):
        def __init__(self):
            self.calls = []

        def process_as_ai_agent(self, intent_text: str):
            self.calls.append(intent_text)
            return super().process_as_ai_agent(intent_text)

    executive = TrackingExecutive()
    facade = RuntimeFacade(settings=settings, gateway=FakeGateway(executive, routes=routes, council=council))

    with pytest.raises(CouncilBudgetExceededError):
        facade.execute("deploy to production")

    # The Executive must never be called for an over-budget Council plan.
    assert executive.calls == []


def test_unrouted_plan_does_not_raise_budget_error(tmp_path: Path):
    settings = Settings(vault_path=tmp_path / "vault")
    council = CouncilPlan("unrouted", None, (), "No eligible agent matched the task.")
    facade = RuntimeFacade(settings=settings, gateway=FakeGateway(FakeExecutive(), routes=[], council=council))

    turn = facade.execute("do something unmatched")

    assert turn.mode == "canonical-executive"
    assert turn.council.mode == "unrouted"
