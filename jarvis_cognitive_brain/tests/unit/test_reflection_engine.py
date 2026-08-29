from jarvis.core.reflection_engine import ReflectionEngine


def test_success_reflection_stays_review():
    result = ReflectionEngine().reflect(
        goal="test goal",
        expected="expected outcome",
        observation={"success": True, "result": "ok"},
        evidence_ids=("mem-1",),
    )
    assert result.success is True
    assert result.lifecycle == "REVIEW"
    assert result.memory_type == "lesson"
    assert result.evidence_ids == ("mem-1",)


def test_failure_reflection_becomes_error_review():
    result = ReflectionEngine().reflect(
        goal="test goal",
        expected="expected outcome",
        observation={"success": False, "error": "boom"},
    )
    assert result.success is False
    assert result.lifecycle == "REVIEW"
    assert result.memory_type == "error"
    assert "boom" in result.lesson
