from pathlib import Path

from jarvis.config import Settings
from jarvis.core.cognitive_gateway import CognitiveGateway


def test_gateway_includes_vault_contract(tmp_path: Path):
    (tmp_path / "AGENTS.md").write_text("MEMORY CONTRACT", encoding="utf-8")
    settings = Settings(vault_path=tmp_path, sync_vault=False)
    gateway = CognitiveGateway(settings=settings)
    prompt = gateway.build_system_prompt("BASE")
    assert prompt.startswith("BASE")
    assert "MEMORY CONTRACT" in prompt


def test_gateway_preserves_local_default():
    settings = Settings(sync_vault=False)
    gateway = CognitiveGateway(settings=settings)
    assert gateway.router.resolve("reasoning").provider == "ollama"
