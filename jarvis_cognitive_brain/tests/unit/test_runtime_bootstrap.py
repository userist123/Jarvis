from __future__ import annotations

from pathlib import Path

from jarvis.config import Settings
from jarvis.runtime.bootstrap import format_status


def test_format_status_includes_local_runtime_contract(tmp_path: Path):
    settings = Settings(
        vault_path=tmp_path / "vault",
        ollama_url="http://localhost:11434",
        ollama_model="test-model",
    )
    assert settings.llm_provider == "ollama"
    assert settings.allow_network is False
    text = format_status(
        type("S", (), {
            "provider": "ollama",
            "ollama_url": settings.ollama_url,
            "ollama_healthy": False,
            "model": settings.ollama_model,
            "vault_path": str(settings.vault_path),
            "vault_present": False,
            "executive_available": False,
            "executive_reason": "vault missing",
            "vault_bridge_available": False,
            "vault_bridge_reason": "vault missing",
        })()
    )
    assert "provider: ollama" in text
    assert "ollama_healthy: False" in text
    assert "vault_present: False" in text
