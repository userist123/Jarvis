from pathlib import Path

from jarvis.config import Settings
from jarvis.llm.model_router import ModelRouter
from jarvis.memory.vault_context import VaultContextLoader


def test_ollama_is_default_provider():
    settings = Settings(_env_file=None)
    assert settings.llm_provider == "ollama"


def test_model_router_resolves_known_capabilities():
    settings = Settings(_env_file=None, ollama_model="local-test-model")
    router = ModelRouter(settings)
    assert router.resolve("coding").model == "local-test-model"
    assert router.resolve("reasoning").provider == "ollama"
    assert router.resolve("unknown").capability == "unknown"


def test_vault_loader_reads_canonical_files(tmp_path: Path):
    (tmp_path / "00_CORE").mkdir()
    (tmp_path / "AGENTS.md").write_text("source of truth", encoding="utf-8")
    (tmp_path / "00_CORE" / "Rules.md").write_text("protect integrity", encoding="utf-8")

    loader = VaultContextLoader(tmp_path)
    context = loader.load()

    assert loader.available()
    assert "source of truth" in context
    assert "protect integrity" in context
