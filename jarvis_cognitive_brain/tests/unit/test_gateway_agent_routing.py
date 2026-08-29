from pathlib import Path

from jarvis.config import Settings
from jarvis.core.cognitive_gateway import CognitiveGateway
from jarvis.llm.mock_provider import MockLLMProvider


def test_gateway_routes_vault_agents_and_escalates_risky_task(tmp_path: Path):
    vault = tmp_path / "vault"
    agent = vault / ".agents" / "security_worker" / "skills" / "security-audit"
    agent.mkdir(parents=True)
    (agent.parent.parent / "BRIEFING.md").write_text(
        "# Briefing\n\n- Archetype: security_worker\n- Target: security audit\n",
        encoding="utf-8",
    )
    (agent / "SKILL.md").write_text("# Security Audit\n", encoding="utf-8")

    gateway = CognitiveGateway(
        settings=Settings(_env_file=None, vault_path=vault),
        provider=MockLLMProvider(),
    )
    routes, plan = gateway.route_agents("security audit network", ("security",), complexity=3)

    assert routes
    assert routes[0].agent == "security_worker"
    assert plan.mode == "council"
    assert plan.primary == "security_worker"
