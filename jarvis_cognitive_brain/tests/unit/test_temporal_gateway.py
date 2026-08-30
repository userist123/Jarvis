from __future__ import annotations

from datetime import date
from pathlib import Path

from jarvis.config import Settings
from jarvis.core.cognitive_gateway import CognitiveGateway


class FakeTemporalBackend:
    def search_memory(self, query: str, limit: int = 20):
        return [{"id": "m1", "content": query}]

    def search_memory_temporal(self, query: str, limit: int = 20, *, as_of=None, known_as_of=None):
        return [{
            "id": "m1",
            "content": query,
            "valid_from": "2020-01-01",
            "valid_until": "2024-12-31",
            "provenance": {"extraction_date": "2021-01-01"},
        }]

    def related_memory(self, note_id: str, limit: int = 20):
        return [{"id": note_id}]

    def propose_memory(self, note):
        return note.get("id")


def test_gateway_uses_temporal_backend_when_available(tmp_path: Path):
    settings = Settings(vault_path=tmp_path, sync_vault=False)
    gateway = CognitiveGateway(settings=settings, provider=None)
    gateway.vault_bridge._backend = FakeTemporalBackend()

    results = gateway.search_vault(
        "Windows Server",
        limit=5,
        as_of=date(2022, 1, 1),
        known_as_of=date(2022, 6, 1),
    )

    assert len(results) == 1
    assert results[0]["id"] == "m1"
