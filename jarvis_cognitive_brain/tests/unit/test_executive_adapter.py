from pathlib import Path

from jarvis.core.executive_adapter import ExecutiveAdapter


class FakeExecutive:
    def process_intent(self, principal, intent_text):
        return {"principal": str(principal), "intent": intent_text, "status": "ok"}


def test_adapter_fails_closed_without_canonical_executive(tmp_path: Path):
    adapter = ExecutiveAdapter(tmp_path)
    assert adapter.available is False
    try:
        adapter.process_as_ai_agent("test")
    except RuntimeError as exc:
        assert "Executive backend unavailable" in str(exc)
    else:
        raise AssertionError("missing Executive must fail closed")


def test_adapter_delegates_to_backend(tmp_path: Path):
    adapter = ExecutiveAdapter(tmp_path, backend=FakeExecutive())
    assert adapter.available is True
    result = adapter.process_intent("ai_agent", "build JARVIS")
    assert result["intent"] == "build JARVIS"
    assert result["status"] == "ok"
