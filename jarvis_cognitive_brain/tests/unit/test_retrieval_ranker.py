from datetime import date

from jarvis.memory.retrieval_ranker import RetrievalRanker


def _note(note_id: str, content: str, **extra):
    data = {
        "id": note_id,
        "content": content,
        "confidence": "high",
        "updated": "2026-08-30",
        "provenance": {"source_type": "user", "source_ref": "test"},
        "lifecycle": "ACTIVE",
        "verification": "verified",
    }
    data.update(extra)
    return data


def test_relevance_drives_ranking():
    ranker = RetrievalRanker()
    ranked = ranker.rank(
        "configure ollama model",
        [_note("a", "configure ollama model locally"), _note("b", "sunrise calendar"), _note("c", "ollama" )],
    )
    assert [row[1].note_id for row in ranked] == ["a", "c", "b"]


def test_authority_and_confidence_contribute_to_score():
    ranker = RetrievalRanker()
    weak = _note("weak", "ollama local model", confidence="low", provenance={"source_type": "ai", "source_ref": "test"})
    strong = _note("strong", "ollama local model", confidence="very_high", provenance={"source_type": "official", "source_ref": "docs"})
    assert ranker.score("ollama local model", strong).final_score > ranker.score("ollama local model", weak).final_score


def test_freshness_decays_with_age():
    ranker = RetrievalRanker()
    fresh = _note("fresh", "fact", updated="2026-08-30")
    old = _note("old", "fact", updated="2024-08-30")
    assert ranker.freshness_score(fresh, date(2026, 8, 30)) > ranker.freshness_score(old, date(2026, 8, 30))


def test_matching_version_gets_bonus_and_mismatch_penalty():
    ranker = RetrievalRanker()
    query = "Python 3.12 virtualenv"
    matching = _note("match", "virtualenv setup", version_range="Python 3.12")
    mismatch = _note("mismatch", "virtualenv setup", version_range="Python 3.10")
    assert ranker.score(query, matching).version_match > 0
    assert ranker.score(query, mismatch).version_match < 0
