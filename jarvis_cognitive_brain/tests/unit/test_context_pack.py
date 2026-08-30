from __future__ import annotations

from jarvis.runtime.context_pack import build_evidence
from jarvis.runtime.facade import RuntimeTurn
from jarvis.runtime.orchestrator import TurnOrchestrator


def test_build_evidence_defaults_to_unverified() -> None:
    items = build_evidence([{"id": "n1", "content": "fact", "provenance": {}}])
    assert items[0].note_id == "n1"
    assert items[0].status == "unverified"


def test_turn_context_marks_conflict() -> None:
    turn = RuntimeTurn(
        mode="canonical-executive",
        intent="x",
        result={
            "status": "success",
            "evidence": [
                {"id": "a", "verification": "verified", "content": "A"},
                {"id": "b", "evidence_status": "conflict", "content": "B"},
            ],
        },
        routes=("agent",),
    )
    orchestrator = object.__new__(TurnOrchestrator)
    context = orchestrator.build_context("x", turn)
    assert "Evidence status: conflict." in context.constraints


def test_context_pack_is_bounded() -> None:
    turn = RuntimeTurn(
        mode="local-chat-fallback",
        intent="x",
        result={"status": "not_executed"},
    )
    orchestrator = object.__new__(TurnOrchestrator)
    context = orchestrator.build_context("x", turn)
    assert len(context.to_prompt(max_chars=100)) <= 100
