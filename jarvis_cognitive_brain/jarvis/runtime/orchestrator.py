"""Conversation turn orchestration over the shared JARVIS runtime facade.

The orchestrator keeps execution results and natural-language generation
separate. It never asks the LLM to invent an execution result.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from jarvis.config import Settings, get_settings
from jarvis.core.cognitive_gateway import CognitiveGateway
from jarvis.runtime.facade import RuntimeFacade, RuntimeTurn


@dataclass(frozen=True)
class ConversationTurn:
    user_text: str
    execution: RuntimeTurn
    response: str


def _execution_summary(turn: RuntimeTurn) -> str:
    result = turn.result
    status = result.get("status", "unknown")
    parts = [
        f"Execution mode: {turn.mode}",
        f"Execution status: {status}",
    ]
    if turn.routes:
        parts.append("Selected agents: " + ", ".join(turn.routes[:5]))
    for key in ("message", "reason", "error", "reflection_memory_generated"):
        value = result.get(key)
        if value:
            parts.append(f"{key}: {value}")
    return "\n".join(parts)


class TurnOrchestrator:
    """Turn-level coordinator shared by future CLI/GUI frontends."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        gateway: Optional[CognitiveGateway] = None,
        facade: Optional[RuntimeFacade] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.gateway = gateway or CognitiveGateway(settings=self.settings)
        self.facade = facade or RuntimeFacade(settings=self.settings, gateway=self.gateway)

    async def respond(self, user_text: str, *, history: Optional[list[dict[str, str]]] = None) -> ConversationTurn:
        execution = self.facade.execute(user_text)
        history = list(history or [])
        context = _execution_summary(execution)
        prompt = (
            "Respond to the user's request using only the execution facts below. "
            "Do not claim an action occurred unless Execution status says success. "
            "If status is blocked, error, or not_executed, explain that plainly.\n\n"
            f"User request:\n{user_text}\n\n"
            f"Execution facts:\n{context}"
        )
        messages = history + [{"role": "user", "content": prompt}]
        response = await self.gateway.chat(
            messages,
            capability="reasoning",
            system_prompt=(
                "You are JARVIS. Turn execution facts into a concise, useful answer. "
                "Never fabricate tool use, memory writes, or completed actions."
            ),
        )
        return ConversationTurn(user_text=user_text, execution=execution, response=response)
