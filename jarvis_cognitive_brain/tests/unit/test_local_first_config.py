from pathlib import Path

from jarvis.config import Settings


def test_local_first_defaults():
    settings = Settings()
    assert settings.llm_provider == "ollama"
    assert settings.ollama_url.startswith("http://")
    assert settings.ollama_model
    assert settings.sync_vault is True


def test_explicit_vault_path_from_environment(monkeypatch, tmp_path: Path):
    vault = tmp_path / "AI_Memory_Vault_CODEX_READY"
    vault.mkdir()
    monkeypatch.setenv("JARVIS_VAULT_PATH", str(vault))
    settings = Settings()
    assert settings.vault_path == vault


def test_capability_models_default_to_base_model():
    settings = Settings(_env_file=None)
    assert settings.ollama_fast_model == ""
    assert settings.ollama_reasoning_model == ""
    assert settings.ollama_coding_model == ""
    assert settings.ollama_vision_model == ""
