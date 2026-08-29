from pathlib import Path

from jarvis.memory.vault_bridge import VaultBridge


class FakeBackend:
    def search_memory(self, query: str, limit: int = 20):
        return [{"id": "1", "content": query}]

    def related_memory(self, note_id: str, limit: int = 20):
        return [{"id": note_id, "relation": "related_to"}]

    def propose_memory(self, note):
        return {"accepted": True, "id": note.get("id")}


def test_bridge_fails_closed_without_backend(tmp_path: Path):
    bridge = VaultBridge(tmp_path)
    assert bridge.available is False
    assert bridge.search_memory("anything") == []
    assert bridge.related_memory("1") == []
    assert bridge.propose_memory({"id": "1"}) is None


def test_bridge_uses_injected_backend(tmp_path: Path):
    bridge = VaultBridge(tmp_path, backend=FakeBackend())
    assert bridge.available is True
    assert bridge.search_memory("hello") == [{"id": "1", "content": "hello"}]
    assert bridge.related_memory("1") == [{"id": "1", "relation": "related_to"}]
    assert bridge.propose_memory({"id": "1"}) == {"accepted": True, "id": "1"}
