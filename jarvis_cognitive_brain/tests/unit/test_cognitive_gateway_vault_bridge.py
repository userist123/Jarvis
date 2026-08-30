from datetime import date
from pathlib import Path

from jarvis.config import Settings
from jarvis.core.cognitive_gateway import CognitiveGateway


class FakeVaultBackend:
    def search_memory(self, query: str, limit: int = 20):
        return [
            {
                "id": "m1",
                "content": query,
                "valid_from": "2024-01-01",
                "valid_until": "2025-12-31",
                "provenance": {"extraction_date": "2024-06-01"},
            }
        ]

    def related_memory(self, note_id: str, limit: int = 20):
        return [{"id": note_id}]

    def propose_memory(self, note):
        return note.get("id")


def test_gateway_constructs_with_vault_bridge(tmp_path: Path):
    settings = Settings(vault_path=tmp_path, sync_vault=False)
    gateway = CognitiveGateway(settings=settings, provider=None)
    assert gateway.vault_bridge.available is False


def test_gateway_can_use_injected_native_backend(tmp_path: Path):
    settings = Settings(vault_path=tmp_path, sync_vault=False)
    gateway = CognitiveGateway(settings=settings, provider=None)
    gateway.vault_bridge._backend = FakeVaultBackend()
    results = gateway.search_vault("hello", limit=5)
    assert results[0]["id"] == "m1"


def test_gateway_search_vault_supports_as_of(tmp_path: Path):
    settings = Settings(vault_path=tmp_path, sync_vault=False)
    gateway = CognitiveGateway(settings=settings, provider=None)
    gateway.vault_bridge._backend = FakeVaultBackend()

    current = gateway.search_vault("hello", as_of=date(2025, 1, 1))
    historical = gateway.search_vault("hello", as_of=date(2023, 1, 1))

    assert [item["id"] for item in current] == ["m1"]
    assert historical == []
