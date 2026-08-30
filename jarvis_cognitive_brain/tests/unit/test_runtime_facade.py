from __future__ import annotations

from pathlib import Path

from jarvis.config import Settings
from jarvis.runtime.facade import RuntimeFacade


class FakeExecutive:
    available = True
    reason = "native Executive loaded"

    def process_as_ai_agent(self, intent_text: str):
        return {"status": "success", "intent": intent_text}


class FakeGateway:
    def __init__(self, executive):
        self.executive = executive

    def route_agents(self, task):
        return ([type("R", (), {"agent": type("A", (), {"name": "test-agent"})()})()], object())

    def process_intent(self, intent_text):
        return self.executive.process_as_ai_agent(intent_text)


def test_facade_prefers_canonical_executive(tmp_path: Path):
    settings = Settings(vault_path=tmp_path / "vault")
    facade = RuntimeFacade(settings=settings, gateway=FakeGateway(FakeExecutive()))
    result = facade.execute("inspect vault")
    assert result.mode == "canonical-executive"
    assert result.routes == ("test-agent",)
    assert result.result["status"] == "success"


def test_facade_is_explicit_when_executive_unavailable(tmp_path: Path):
    settings = Settings(vault_path=tmp_path / "vault")
    unavailable = type("E", (), {"available": False, "reason": "vault missing"})()
    facade = RuntimeFacade(settings=settings, gateway=FakeGateway(unavailable))
    result = facade.execute("inspect vault")
    assert result.mode == "local-chat-fallback"
    assert result.result["status"] == "not_executed"
    assert result.result["reason"] == "vault missing"
