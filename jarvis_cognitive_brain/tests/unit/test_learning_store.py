from pathlib import Path

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


def test_learning_cases_survive_restart(tmp_path: Path):
    store_path = tmp_path / ".jarvis" / "learning_cases.json"
    bridge1 = VaultBridge(".", backend=FakeBackend())
    loop1 = LearningLoop(bridge1, store_path=str(store_path))
    loop1.learn(
        goal="demo",
        expected="done",
        observation={"status": "success", "result": "ok", "observed_at": "2026-08-30T10:00:00+00:00"},
        evidence_ids=("ev-1",),
    )
    assert loop1.last_learning_case.occurrences == 1

    bridge2 = VaultBridge(".", backend=FakeBackend())
    loop2 = LearningLoop(bridge2, store_path=str(store_path))
    loop2.learn(
        goal="demo",
        expected="done",
        observation={"status": "success", "result": "ok", "observed_at": "2026-08-30T11:00:00+00:00"},
        evidence_ids=("ev-2",),
    )

    assert loop2.last_learning_case.occurrences == 2
    assert loop2.last_learning_case.evidence_ids == {"ev-1", "ev-2"}
