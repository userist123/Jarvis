from jarvis.memory.graph_recall import GraphRecall


def test_graph_recall_expands_explicit_relation():
    seed = {
        "id": "a",
        "content": "primary",
        "relations": [{"relation": "supports", "target_id": "b"}],
    }
    related = {"id": "b", "content": "supporting note", "relations": []}
    expanded = GraphRecall().expand([seed], {"a": seed, "b": related})
    ids = {item["id"] for item in expanded}
    assert ids == {"a", "b"}
    child = next(item for item in expanded if item["id"] == "b")
    assert child["graph_hops"] == 1
    assert child["graph_bonus"] > 0


def test_graph_recall_does_not_invent_missing_edges():
    seed = {"id": "a", "content": "primary", "relations": []}
    related = {"id": "b", "content": "unrelated", "relations": []}
    expanded = GraphRecall().expand([seed], {"a": seed, "b": related})
    assert [item["id"] for item in expanded] == ["a"]


def test_graph_recall_is_bounded_by_hops():
    a = {"id": "a", "relations": [{"relation": "related_to", "target_id": "b"}]}
    b = {"id": "b", "relations": [{"relation": "related_to", "target_id": "c"}]}
    c = {"id": "c", "relations": []}
    expanded = GraphRecall(max_hops=1).expand([a], {"a": a, "b": b, "c": c})
    assert {item["id"] for item in expanded} == {"a", "b"}
