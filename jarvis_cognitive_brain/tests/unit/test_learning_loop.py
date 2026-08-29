from jarvis.core.learning_loop import LearningLoop
from jarvis.memory.vault_bridge import VaultBridge


class FakeBackend:
    def __init__(self):
        self.proposals = []

    def search_memory(self, query, limit=20):
        return []

    def related_memory(self, note_id, limit=20):
        return []

    def propose_memory(self, note):
        self.proposals.append(note)
        return {"accepted": True, "lifecycle": note["lifecycle"]}


def test_learning_loop_persists_review_only():
    backend = FakeBackend()
    bridge = VaultBridge(".", backend=backend)
    result, persisted = LearningLoop(bridge).learn(
        goal="demo",
        expected="done",
        observation={"success": True, "result": "ok"},
        evidence_ids=("obs-1",),
    )
    assert result.lifecycle == "REVIEW"
    assert persisted["lifecycle"] == "REVIEW"
    assert backend.proposals[0]["verification"] == "unverified"
    assert backend.proposals[0]["provenance"]["evidence_ids"] == ["obs-1"]
