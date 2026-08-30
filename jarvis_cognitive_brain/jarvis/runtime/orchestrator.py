"""Conversation turn orchestration over the shared JARVIS runtime facade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from jarvis.config import Settings, get_settings
from jarvis.core.cognitive_gateway import CognitiveGateway
from jarvis.runtime.context_pack import ContextPack, build_evidence
from jarvis.runtime.facade import RuntimeFacade, RuntimeTurn


@dataclass(frozen=True)
class ConversationTurn:
    user_text: str
    execution: RuntimeTurn
    context: ContextPack
    response: str


def _evidence_from_execution(result: dict[str, Any]) -> tuple:
    candidates = result.get("evidence") or result.get("memories") or []
    return build_evidence(candidates) if isinstance(candidates, list) else ()


def _status_constraints(status: str) -> tuple[str, ...]:
    if status == "success":
        return ("Only report actions represented by execution facts.",)
    if status == "blocked":
        return ("Explain that execution was blocked and do not imply completion.",)
    if status == "error":
        return ("Explain the execution error and do not imply completion.",)
    return ("State that the action was not executed.",)


class TurnOrchestrator:
    """Turn-level coordinator shared by CLI/GUI frontends."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        gateway: Optional[CognitiveGateway] = None,
        facade: Optional[RuntimeFacade] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.gateway = gateway or CognitiveGateway(settings=self.settings)
        self.facade = facade or RuntimeFacade(settings=self.settings, gateway=self.gateway)

    def build_context(self, user_text: str, execution: RuntimeTurn) -> ContextPack:
        result = execution.result
        evidence = _evidence_from_execution(result)
        statuses = {item.status for item in evidence}
        if "conflict" in statuses:
            evidence_status = "conflict"
        elif "verified" in statuses:
            evidence_status = "verified"
        else:
            evidence_status = "unverified" if evidence else "unverified"
        constraints = list(_status_constraints(str(result.get("status", "unknown"))))
        constraints.append(f"Evidence status: {evidence_status}.")
        return ContextPack(
            intent=user_text,
            mode=execution.mode,
            agents=execution.routes,
            evidence=evidence,
            constraints=tuple(constraints),
        )

    async def respond(
        self,
        user_text: str,
        *,
        history: Optional[list[dict[str, str]]] = None,
    ) -> ConversationTurn:
        execution = self.facade.execute(user_text)
        context = self.build_context(user_text, execution)
        prompt = (
            "Respond to the user's request using the grounded context pack below. "
            "Do not invent actions, evidence, provenance, or memory writes. "
            "Do not reveal hidden chain-of-thought; provide conclusions and concise reasons only.\n\n"
            f"{context.to_prompt(max_chars=12000)}"
        )
        messages = list(history or []) + [{"role": "user", "content": prompt}]
        response = await self.gateway.chat(
            messages,
            capability="reasoning",
            system_prompt=(
                "You are JARVIS. Treat the supplied execution facts and evidence as authoritative. "
                "If evidence is unverified or conflicting, say so explicitly."
            ),
        )
        return ConversationTurn(
            user_text=user_text,
            execution=execution,
            context=context,
            response=response,
        )
