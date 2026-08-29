from jarvis.memory.retrieval_ranker import RetrievalRanker


def test_graph_bonus_is_bounded_and_auditable():
    ranker = RetrievalRanker(max_graph_bonus=0.12)
    note = {
        "id": "b",
        "content": "supporting memory",
        "confidence": "high",
        "provenance": {"source_type": "user", "source_ref": "test"},
        "updated": "2026-08-30",
        "graph_bonus": 0.50,
    }
    score = ranker.score("supporting memory", note)
    assert score.graph_bonus == 0.12
    assert "graph_bonus=+0.12" in score.reason
