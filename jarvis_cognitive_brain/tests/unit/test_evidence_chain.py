from jarvis.memory.evidence_chain import EvidenceChain


def note(note_id, content, verification="verified"):
    return {
        "id": note_id,
        "content": content,
        "verification": verification,
        "confidence": "high",
        "updated": "2026-08-30",
        "provenance": {"source_type": "user", "source_ref": "test"},
        "lifecycle": "active",
    }


def test_verified_evidence_is_usable():
    result = EvidenceChain().build("sqlite memory", [note("a", "SQLite memory storage")])
    assert result.usable
    assert result.status == "verified"
    assert result.evidence[0].note_id == "a"


def test_conflict_is_reported_and_excluded():
    left = note("a", "SQLite is the canonical memory store")
    right = note("b", "PostgreSQL is the canonical memory store")
    result = EvidenceChain().build("canonical memory store", [left, right], conflicts=[(left, right)])
    assert not result.usable
    assert result.status == "conflict"
    assert set(result.conflicts) == {"a", "b"}


def test_unverified_evidence_is_not_marked_verified():
    result = EvidenceChain().build("memory", [note("a", "possible memory", verification="unverified")])
    assert result.usable
    assert result.status == "unverified"
