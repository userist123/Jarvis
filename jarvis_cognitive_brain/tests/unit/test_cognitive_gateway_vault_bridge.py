from pathlib import Path

from jarvis.config import Settings
from jarvis.core.cognitive_gateway import CognitiveGateway


class FakeVaultBackend:
    def search_memory(self, query: str, limit: int = 20):
        return [{"id": "m1", "content": query}]

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
    assert results == [{"id": "m1", "content": "hello"}]
