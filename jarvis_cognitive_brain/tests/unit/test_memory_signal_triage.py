from jarvis.runtime.memory_signal_triage import triage_signal, triage_signals


def test_contradiction_routes_to_conflict_review():
    result = triage_signal({
        "signal_id": "s1",
        "signal_type": "POTENTIAL_CONTRADICTION",
        "severity": "high",
        "confidence": 0.65,
    })
    assert result.route == "CONFLICT_REVIEW"
    assert result.priority == "urgent"
    assert result.read_only if hasattr(result, "read_only") else True


def test_duplicate_routes_to_learning_review():
    result = triage_signal({
        "signal_id": "s2",
        "signal_type": "DUPLICATE",
        "severity": "medium",
        "confidence": 1.0,
    })
    assert result.route == "LEARNING_REVIEW"
    assert result.priority == "high"


def test_stale_routes_to_memory_review():
    result = triage_signal({
        "signal_id": "s3",
        "signal_type": "STALE",
        "severity": "medium",
        "confidence": 0.95,
    })
    assert result.route == "MEMORY_REVIEW"
    assert result.priority == "high"


def test_gap_routes_to_knowledge_acquisition():
    result = triage_signal({
        "signal_id": "s4",
        "signal_type": "KNOWLEDGE_GAP",
        "severity": "low",
        "confidence": 0.90,
    })
    assert result.route == "KNOWLEDGE_ACQUISITION"
    assert result.priority == "normal"


def test_unknown_signal_is_manual_review():
    result = triage_signal({
        "signal_id": "s5",
        "signal_type": "NEW_TYPE",
        "severity": "low",
        "confidence": 0.2,
    })
    assert result.route == "MANUAL_REVIEW"
    assert result.priority == "low"


def test_triage_order_is_deterministic():
    results = triage_signals([
        {"signal_id": "low", "signal_type": "KNOWLEDGE_GAP", "severity": "low", "confidence": 0.2},
        {"signal_id": "urgent", "signal_type": "POTENTIAL_CONTRADICTION", "severity": "high", "confidence": 0.65},
        {"signal_id": "high", "signal_type": "DUPLICATE", "severity": "medium", "confidence": 1.0},
    ])
    assert [item.signal_id for item in results] == ["urgent", "high", "low"]
