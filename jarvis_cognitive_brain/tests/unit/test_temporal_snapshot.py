from jarvis.config import Settings
from jarvis.core.cognitive_gateway import CognitiveGateway


class FakeBackend:
    def search_memory(self, query, limit=20):
        return [{"id": "m1", "content": query}]

    def search_memory_temporal_pack(self, query, limit=20, *, as_of=None, known_as_of=None):
        return {
            "results": [{"id": "m1", "content": query}],
            "temporal": {
                "as_of": str(as_of),
                "known_as_of": str(known_as_of),
                "conflicts": [
                    {"left_id": "m1", "right_id": "m2", "status": "potential_conflict"}
                ],
            },
        }

    def related_memory(self, note_id, limit=20):
        return []

    def propose_memory(self, note):
        return note.get("id")


def test_temporal_snapshot_preserves_conflicts(tmp_path):
    settings = Settings(vault_path=tmp_path, sync_vault=False)
    gateway = CognitiveGateway(settings=settings, provider=None)
    gateway.vault_bridge._backend = FakeBackend()

    snapshot = gateway.search_vault_snapshot(
        "server support", as_of="2023-01-01", known_as_of="2023-06-01"
    )

    assert snapshot["results"][0]["id"] == "m1"
    assert snapshot["conflicts"][0]["status"] == "potential_conflict"
