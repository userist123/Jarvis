from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from jarvis.config import Settings, get_settings
from jarvis.llm.base import BaseLLMProvider, CancellationToken
from jarvis.llm.model_router import ModelRouter
from jarvis.memory.vault_context import VaultContextLoader
from jarvis.memory.vault_bridge import VaultBridge
from jarvis.core.executive_adapter import ExecutiveAdapter
from jarvis.core.cognitive_session import CognitiveSession
from jarvis.core.session_manager import SessionManager, SessionResumeResult
from jarvis.core.learning_loop import LearningLoop
from jarvis.core.reflection_engine import ReflectionResult
from jarvis.agents.agent_council import AgentCouncil, CouncilPlan
from jarvis.agents.agent_registry import AgentRegistry
from jarvis.agents.agent_router import AgentRoute, AgentRouter


class CognitiveGateway:
    """Single entry point for memory-grounded, provider-neutral reasoning."""

    def __init__(self, settings: Optional[Settings] = None, provider: Optional[BaseLLMProvider] = None) -> None:
        self.settings = settings or get_settings()
        self.router = ModelRouter(self.settings)
        self.vault = VaultContextLoader(settings=self.settings)
        self.vault_bridge = VaultBridge(self.settings.vault_path)
        self.executive = ExecutiveAdapter(self.settings.vault_path)
        self.sessions = SessionManager(self.settings)
        self.learning = LearningLoop(self.vault_bridge)
        self.agent_registry = AgentRegistry(self.settings.vault_path)
        self.agent_router: AgentRouter = self.agent_registry.build_router()
        self.agent_council = AgentCouncil(
            risky_capabilities=("iot", "iot_control", "execute_code", "network", "security")
        )
        self._provider_override = provider

    def provider(self, capability: str = "reasoning") -> BaseLLMProvider:
        return self._provider_override or self.router.provider(capability)

    def route_agents(
        self,
        task: str,
        required_capabilities: tuple[str, ...] = (),
        *,
        complexity: int = 1,
        require_review: bool = False,
    ) -> tuple[list[AgentRoute], CouncilPlan]:
        routes = self.agent_router.rank(task, required_capabilities)
        plan = self.agent_council.plan(
            routes,
            required_capabilities,
            complexity=complexity,
            require_review=require_review,
        )
        return routes, plan

    def search_vault(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        """Search native Vault memory when available; otherwise return no native hits."""
        return self.vault_bridge.search_memory(query, limit=limit)

    def process_intent(self, intent_text: str) -> dict[str, Any]:
        """Delegate an intent to the canonical Vault Executive when available."""
        return self.executive.process_as_ai_agent(intent_text)

    def new_session(self, goal: str = "") -> CognitiveSession:
        return self.sessions.create(goal)

    def save_session(self, session: CognitiveSession) -> str:
        return str(self.sessions.save(session))

    def resume_session(self, session_id: str) -> SessionResumeResult:
        return self.sessions.resume(session_id)

    def reflect_and_learn(
        self,
        *,
        goal: str,
        expected: str,
        observation: Mapping[str, Any],
        evidence_ids: tuple[str, ...] = (),
    ) -> tuple[ReflectionResult, Any]:
        """Reflect on an outcome and submit only a REVIEW proposal."""
        return self.learning.learn(
            goal=goal,
            expected=expected,
            observation=observation,
            evidence_ids=evidence_ids,
        )

    def build_system_prompt(self, base_prompt: str = "", max_chars: int = 24000) -> str:
        context = self.vault.load(max_chars=max_chars)
        parts = [base_prompt.strip()] if base_prompt.strip() else []
        if context:
            parts.append("Canonical AI Memory Vault operating context:\n" + context)
        return "\n\n".join(parts).strip()

    async def generate(self, prompt: str, capability: str = "reasoning", system_prompt: str = "", cancellation_token: Optional[CancellationToken] = None, **kwargs: Any) -> str:
        return await self.provider(capability).generate(prompt, system_prompt=self.build_system_prompt(system_prompt), cancellation_token=cancellation_token, **kwargs)

    async def chat(self, messages: list[Dict[str, str]], capability: str = "reasoning", system_prompt: str = "", cancellation_token: Optional[CancellationToken] = None, **kwargs: Any) -> str:
        effective = list(messages)
        grounded = self.build_system_prompt(system_prompt)
        if grounded:
            effective.insert(0, {"role": "system", "content": grounded})
        return await self.provider(capability).chat(effective, cancellation_token=cancellation_token, **kwargs)
