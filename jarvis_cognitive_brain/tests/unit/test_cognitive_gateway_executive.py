from pathlib import Path

from jarvis.core.cognitive_gateway import CognitiveGateway


class FakeExecutive:
    def process_intent(self, principal, intent_text):
        return {"intent": intent_text, "principal": str(principal), "status": "delegated"}


def test_gateway_delegates_intent_to_executive(tmp_path: Path):
    gateway = CognitiveGateway.__new__(CognitiveGateway)
    gateway.executive = type("Adapter", (), {"process_as_ai_agent": lambda self, text: FakeExecutive().process_intent("ai_agent", text)})()
    result = gateway.process_intent("inspect vault")
    assert result["intent"] == "inspect vault"
    assert result["status"] == "delegated"
