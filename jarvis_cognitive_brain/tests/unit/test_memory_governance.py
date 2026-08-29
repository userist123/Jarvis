from jarvis.memory.memory_governance import MemoryGovernance


def _note(content: str, *, note_id: str, source: str = "user", version: str = "1.0"):
    return {
        "id": note_id,
        "content": content,
        "applies_to": "test-product",
        "version_range": version,
        "provenance": {"source_type": source, "source_ref": f"test:{note_id}"},
        "lifecycle": "REVIEW",
        "verification": "verified",
    }


def test_duplicate_requires_matching_scope():
    g = MemoryGovernance()
    candidate = _note("Use SQLite for memory storage", note_id="new")
    existing = _note("Use SQLite for memory storage", note_id="old", version="2.0")
    decision = g.inspect_candidate(candidate, [existing])
    assert decision.action == "create"


def test_duplicate_with_same_scope_is_update():
    g = MemoryGovernance()
    candidate = _note("Use SQLite for memory storage", note_id="new")
    existing = _note("Use SQLite for memory storage", note_id="old")
    decision = g.inspect_candidate(candidate, [existing])
    assert decision.action == "update"
    assert decision.matched_id == "old"
    assert decision.similarity == 1.0


def test_missing_provenance_requires_review():
    g = MemoryGovernance()
    candidate = _note("Useful memory", note_id="new")
    candidate["provenance"] = {}
    decision = g.inspect_candidate(candidate, [])
    assert decision.action == "review"


def test_unverified_candidate_does_not_activate():
    g = MemoryGovernance()
    candidate = _note("Potential fact", note_id="new")
    candidate["verification"] = "unverified"
    decision = g.inspect_candidate(candidate, [])
    assert decision.action == "review"


def test_fingerprint_is_stable():
    g = MemoryGovernance()
    assert g.fingerprint("Hello,   WORLD!") == g.fingerprint("hello world")
