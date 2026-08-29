from datetime import date

from jarvis.memory.retrieval_ranker import RetrievalRanker


def test_unknown_version_is_neutral():
    ranker = RetrievalRanker()
    note = {"id": "1", "content": "ollama", "version_range": "", "confidence": "high", "updated": "2026-08-30", "provenance": {"source_type": "user", "source_ref": "x"}}
    assert ranker.score("Ollama 1.2", note).version_match == 0.0


def test_archived_memory_is_penalized_but_still_ranked():
    ranker = RetrievalRanker()
    note = {"id": "1", "content": "ollama configuration", "confidence": "high", "updated": "2026-08-30", "lifecycle": "ARCHIVED", "verification": "verified", "provenance": {"source_type": "user", "source_ref": "x"}}
    score = ranker.score("ollama configuration", note)
    assert score.final_score < 1.0
    assert score.note_id == "1"


def test_freshness_has_stable_default_for_missing_date():
    ranker = RetrievalRanker()
    note = {"id": "1", "content": "fact", "confidence": "high", "provenance": {"source_type": "user", "source_ref": "x"}}
    assert ranker.freshness_score(note, date(2026, 8, 30)) == 0.5
