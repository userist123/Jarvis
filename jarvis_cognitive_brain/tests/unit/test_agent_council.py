from jarvis.agents.agent_council import AgentCouncil
from jarvis.agents.agent_router import AgentRoute


def _route(name: str, score: float) -> AgentRoute:
    return AgentRoute(name, score, (), (), "test")


def test_simple_task_uses_single_agent():
    plan = AgentCouncil(complexity_threshold=3).plan([_route("backend", 1.0), _route("database", 0.9)], ["backend"], complexity=1)
    assert plan.mode == "single"
    assert plan.primary == "backend"
    assert plan.reviewers == ()


def test_complex_task_uses_council():
    plan = AgentCouncil(complexity_threshold=3).plan([_route("backend", 1.0), _route("security", 0.9), _route("database", 0.8)], ["backend"], complexity=3)
    assert plan.mode == "council"
    assert plan.primary == "backend"
    assert plan.reviewers == ("security", "database")


def test_risky_capability_forces_review():
    council = AgentCouncil(complexity_threshold=5, risky_capabilities=["execute_code"])
    plan = council.plan([_route("coder", 1.0), _route("security", 0.8)], ["execute_code"], complexity=1)
    assert plan.mode == "council"
