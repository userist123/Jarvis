from jarvis.agents.agent_router import AgentProfile, AgentRouter


def test_routes_by_required_capability():
    router = AgentRouter([
        AgentProfile("local_ai_engineer", ("local_ai", "ollama"), ("ollama", "local"), priority=0.2),
        AgentProfile("backend_systems_engineer", ("backend", "database"), ("api", "backend"), priority=0.1),
    ])
    route = router.route("configure local Ollama model", ["local_ai", "ollama"])
    assert route is not None
    assert route.agent == "local_ai_engineer"


def test_disabled_agent_is_ignored():
    router = AgentRouter([
        AgentProfile("local_ai_engineer", ("local_ai",), ("ollama",), enabled=False),
        AgentProfile("backend_systems_engineer", ("backend",), ("api",), priority=0.1),
    ])
    assert router.route("ollama", ["local_ai"]) is None


def test_keyword_matching_breaks_ties_deterministically():
    router = AgentRouter([
        AgentProfile("backend_systems_engineer", ("backend",), ("api",)),
        AgentProfile("database_and_persistence_engineer", ("backend",), ("database",)),
    ])
    route = router.route("database migration", ["backend"])
    assert route is not None
    assert route.agent == "database_and_persistence_engineer"
