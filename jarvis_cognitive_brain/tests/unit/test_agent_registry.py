from pathlib import Path

from jarvis.agents.agent_registry import AgentRegistry


def test_discovers_agent_workspace_and_skills(tmp_path: Path):
    vault = tmp_path / "vault"
    agent = vault / ".agents" / "forensic_auditor" / "skills" / "vault-security-audit"
    agent.mkdir(parents=True)
    (agent.parent.parent / "BRIEFING.md").write_text(
        "# Briefing\n\n- Archetype: forensic_auditor\n- Target: security audit\n",
        encoding="utf-8",
    )
    (agent / "SKILL.md").write_text("# Vault Security Audit\n", encoding="utf-8")

    registry = AgentRegistry(vault)
    artifacts = registry.discover()

    assert len(artifacts) == 1
    assert artifacts[0].name == "forensic_auditor"
    assert artifacts[0].archetype == "forensic_auditor"
    assert len(artifacts[0].skills) == 1


def test_registry_excludes_global_skills_folder(tmp_path: Path):
    skills = tmp_path / ".agents" / "skills"
    skills.mkdir(parents=True)
    (skills / "SKILL.md").write_text("# Global", encoding="utf-8")

    registry = AgentRegistry(tmp_path)
    assert registry.discover() == ()


def test_to_profiles_contains_skill_tokens(tmp_path: Path):
    agent = tmp_path / ".agents" / "security_worker" / "skills" / "vault-security-audit"
    agent.mkdir(parents=True)
    (agent / "SKILL.md").write_text("# Security Audit", encoding="utf-8")

    profiles = AgentRegistry(tmp_path).to_profiles()
    assert len(profiles) == 1
    assert "security" in profiles[0].keywords
    assert "audit" in profiles[0].keywords
