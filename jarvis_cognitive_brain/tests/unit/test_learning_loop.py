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
        return {"accepted": True, "id": note["id"], "lifecycle": note["lifecycle"]}


def test_learning_loop_persists_review_only():
    backend = FakeBackend()
    bridge = VaultBridge(".", backend=backend)
    result, persisted = LearningLoop(bridge).learn(
        goal="demo",
        expected="done",
        observation={"success": True, "result": "ok"},
        evidence_ids=("obs-1",),
    )
    proposal = backend.proposals[0]
    assert result.lifecycle == "REVIEW"
    assert persisted["lifecycle"] == "REVIEW"
    assert proposal["id"].startswith("lrn-")
    assert proposal["verification"] == "unverified"
    assert proposal["category"] == "learning"
    assert proposal["provenance"]["source_type"] == "ai"
    assert proposal["provenance"]["evidence_ids"] == ["obs-1"]


def test_learning_proposal_id_is_deterministic():
    backend = FakeBackend()
    bridge = VaultBridge(".", backend=backend)
    loop = LearningLoop(bridge)
    kwargs = {
        "goal": "demo",
        "expected": "done",
        "observation": {"success": True, "result": "ok"},
        "evidence_ids": ("obs-1", "obs-2"),
    }
    loop.learn(**kwargs)
    loop.learn(**kwargs)
    assert backend.proposals[0]["id"] == backend.proposals[1]["id"]
