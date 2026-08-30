from __future__ import annotations

import pytest

from jarvis.runtime.facade import RuntimeTurn
from jarvis.runtime.orchestrator import TurnOrchestrator


class FakeGateway:
    def __init__(self, response: str = "final answer") -> None:
        self.response = response

    async def chat(self, messages, capability="reasoning", system_prompt="", **kwargs):
        assert messages[-1]["role"] == "user"
        return self.response


class FakeFacade:
    def __init__(self, result: RuntimeTurn) -> None:
        self.result = result

    def execute(self, intent: str) -> RuntimeTurn:
        assert intent
        return self.result


@pytest.mark.asyncio
async def test_orchestrator_does_not_claim_success_when_execution_failed():
    turn = RuntimeTurn(
        mode="canonical-executive",
        intent="do task",
        result={"status": "blocked", "reason": "approval required"},
        routes=("test-agent",),
    )
    result = await TurnOrchestrator(
        gateway=FakeGateway("blocked plainly"),
        facade=FakeFacade(turn),
    ).respond("do task")

    assert result.execution.result["status"] == "blocked"
    assert result.response == "blocked plainly"


@pytest.mark.asyncio
async def test_orchestrator_passes_execution_facts_to_llm():
    turn = RuntimeTurn(
        mode="canonical-executive",
        intent="do task",
        result={"status": "success", "message": "completed"},
        routes=("test-agent",),
    )
    gateway = FakeGateway("done")
    result = await TurnOrchestrator(gateway=gateway, facade=FakeFacade(turn)).respond("do task")

    assert result.response == "done"
