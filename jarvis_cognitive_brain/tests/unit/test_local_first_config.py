from pathlib import Path

from jarvis.config import Settings


def test_local_first_defaults():
    settings = Settings()
    assert settings.llm_provider == "ollama"
    assert settings.ollama_url.startswith("http://")
    assert settings.ollama_model


def test_explicit_vault_path_from_environment(monkeypatch, tmp_path: Path):
    vault = tmp_path / "AI_Memory_Vault_CODEX_READY"
    vault.mkdir()
    monkeypatch.setenv("JARVIS_VAULT_PATH", str(vault))
    settings = Settings()
    assert settings.vault_path == vault
