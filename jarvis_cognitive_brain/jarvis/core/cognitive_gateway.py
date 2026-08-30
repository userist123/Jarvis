from __future__ import annotations

from datetime import date
from typing import Any, Dict, Mapping, Optional

from jarvis.config import Settings, get_settings
from jarvis.llm.base import BaseLLMProvider, CancellationToken
from jarvis.llm.model_router import ModelRouter
from jarvis.memory.vault_context import VaultContextLoader
from jarvis.memory.vault_bridge import VaultBridge
from jarvis.runtime.temporal import TemporalQuery, filter_temporal
from jarvis.runtime.learning_review_filters import build_filtered_queue
from jarvis.runtime.learning_review_session import LearningReviewSessionService
from jarvis.runtime.learning_review_dashboard import ReviewerDashboardService
from jarvis.runtime.governance_center import GovernanceCenterService
from jarvis.runtime.case_materialization_service import CaseMaterializationService
from jarvis.runtime.review_lifecycle import ReviewLifecycleService
from jarvis.runtime.windows_identity import WindowsIdentityProvider
from jarvis.runtime.reviewer_identity import ReviewerIdentity
from jarvis.core.executive_adapter import ExecutiveAdapter
from jarvis.core.cognitive_session import CognitiveSession
from jarvis.core.session_manager import SessionManager, SessionResumeResult
from jarvis.core.learning_loop import LearningLoop
from jarvis.core.reflection_engine import ReflectionResult
from jarvis.runtime.conflict_review import ConflictReviewService
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
        self.learning_store = self.learning.store
        self.learning_review_queue_service = LearningReviewSessionService(self.learning_store)
        self.learning_dashboard_service = ReviewerDashboardService(self.learning_store)
        self.review_lifecycle = ReviewLifecycleService()
        self.conflict_reviews = ConflictReviewService(self.vault_bridge)
        self.governance_center_service = GovernanceCenterService(self.learning_store, self.conflict_reviews.review_states)
        self.case_materialization_service = CaseMaterializationService(
            conflict_service=self.conflict_reviews,
        )
        self.reviewer_identity = WindowsIdentityProvider(
            admin_subjects=frozenset(str(x).strip() for x in self.settings.reviewer_admin_subjects if str(x).strip())
        ).resolve()
        self.agent_registry = AgentRegistry(self.settings.vault_path)
        self.agent_router: AgentRouter = self.agent_registry.build_router()
        self.agent_council = AgentCouncil(risky_capabilities=("iot", "iot_control", "execute_code", "network", "security"))
        self._provider_override = provider

    def current_reviewer_identity(self) -> ReviewerIdentity:
        return self.reviewer_identity

    def governance_center(self, *, risk: str | None = None, min_confidence: float | None = None, top_n: int = 10) -> dict[str, Any]:
        return self.governance_center_service.build(identity=self.reviewer_identity.as_dict(), risk=risk, min_confidence=min_confidence, top_n=top_n).as_dict()

    def memory_case(self, signal: Mapping[str, Any]) -> dict[str, Any]:
        return self.case_materialization_service.materialize_signal(signal)

    def memory_cases(self) -> list[dict[str, Any]]:
        return self.case_materialization_service.list_cases()

    def memory_cases_from_signals(self, signals: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
        return self.case_materialization_service.materialize_many(signals)

    def provider(self, capability: str = "reasoning") -> BaseLLMProvider:
        return self._provider_override or self.router.provider(capability)

    def route_agents(self, task: str, required_capabilities: tuple[str, ...] = (), *, complexity: int = 1, require_review: bool = False) -> tuple[list[AgentRoute], CouncilPlan]:
        routes = self.agent_router.rank(task, required_capabilities)
        plan = self.agent_council.plan(routes, required_capabilities, complexity=complexity, require_review=require_review)
        return routes, plan

    def search_vault(self, query: str, limit: int = 20, *, as_of: date | str | None = None, known_as_of: date | str | None = None) -> list[dict[str, Any]]:
        temporal = TemporalQuery.from_values(as_of=as_of, known_as_of=known_as_of)
        if temporal.as_of is None and temporal.known_as_of is None:
            return self.vault_bridge.search_memory(query, limit=limit)
        results = self.vault_bridge.search_memory_temporal(query, limit=limit, as_of=temporal.as_of, known_as_of=temporal.known_as_of)
        return list(filter_temporal(results, temporal))

    def search_vault_snapshot(self, query: str, limit: int = 20, *, as_of: date | str | None = None, known_as_of: date | str | None = None) -> dict[str, Any]:
        temporal = TemporalQuery.from_values(as_of=as_of, known_as_of=known_as_of)
        if temporal.as_of is None and temporal.known_as_of is None:
            return {"results": self.vault_bridge.search_memory(query, limit=limit), "temporal": None, "conflicts": []}
        pack = self.vault_bridge.search_memory_temporal_pack(query, limit=limit, as_of=temporal.as_of, known_as_of=temporal.known_as_of)
        results = list(pack.get("results", pack.get("items", [])))
        filtered = list(filter_temporal(results, temporal))
        return {"results": filtered, "temporal": pack.get("temporal"), "conflicts": list((pack.get("temporal") or {}).get("conflicts", []))}

    def learning_review_queue(self, *, risk: str | None = None, promotable: bool | None = None, min_confidence: float | None = None, as_of: date | str | None = None, known_as_of: date | str | None = None) -> list[dict[str, Any]]:
        return [item.as_dict() for item in build_filtered_queue(self.learning_store.records(), risk=risk, promotable=promotable, min_confidence=min_confidence, as_of=as_of, known_as_of=known_as_of)]

    def reviewer_dashboard(self, *, risk: str | None = None, promotable: bool | None = None, min_confidence: float | None = None, as_of: date | str | None = None, known_as_of: date | str | None = None, top_n: int = 10) -> dict[str, Any]:
        return self.learning_dashboard_service.build(risk=risk, promotable=promotable, min_confidence=min_confidence, as_of=as_of, known_as_of=known_as_of, top_n=top_n).as_dict()

    def open_learning_review_session(self, case_id: str, *, as_of: date | str | None = None, known_as_of: date | str | None = None) -> dict[str, Any]:
        return self.learning_review_queue_service.open(case_id, as_of=as_of, known_as_of=known_as_of).as_dict()

    def open_conflict_review(self, *, memory_ids: tuple[str, ...] | list[str], reasons: tuple[str, ...] | list[str], conflict_type: str = "semantic", evidence_ids: tuple[str, ...] | list[str] = (), as_of: date | str | None = None, known_as_of: date | str | None = None) -> dict[str, Any]:
        return self.conflict_reviews.open_case(memory_ids=memory_ids, reasons=reasons, conflict_type=conflict_type, evidence_ids=evidence_ids, as_of=as_of, known_as_of=known_as_of)

    def transition_review_state(self, *, case_id: str, target: str, actor: str, reason: str) -> dict[str, Any]:
        return self.conflict_reviews.transition_review(case_id=case_id, target=target, actor=actor, reason=reason)

    def get_review_state(self, case_id: str) -> dict[str, Any]:
        return self.conflict_reviews.review_state(case_id)

    def acquire_conflict_evidence(self, *, memory_ids: tuple[str, ...] | list[str], conflict_case_id: str | None = None, as_of: date | str | None = None, known_as_of: date | str | None = None) -> dict[str, Any]:
        return self.conflict_reviews.acquire_evidence(memory_ids=memory_ids, conflict_case_id=conflict_case_id, as_of=as_of, known_as_of=known_as_of)

    def verify_conflict_evidence(self, *, bundle: dict[str, Any]) -> dict[str, Any]:
        return self.conflict_reviews.verify_evidence(bundle=bundle)

    def verify_and_advance_conflict_review(self, *, bundle: dict[str, Any]) -> dict[str, Any]:
        verification = self.conflict_reviews.verify_evidence(bundle=bundle)
        case_id = str(bundle.get("conflict_case_id") or "")
        return {"verification": verification, "review_state": self.get_review_state(case_id) if case_id else None}

    def issue_conflict_verdict(self, *, principal: str, reviewer: str, verdict: str, memory_ids: tuple[str, ...] | list[str], evidence_bundle_hash: str, evidence_valid: bool, reason: str, as_of: date | str | None = None, known_as_of: date | str | None = None) -> dict[str, Any]:
        return self.conflict_reviews.issue_verdict(principal=principal, reviewer=reviewer, verdict=verdict, memory_ids=memory_ids, evidence_bundle_hash=evidence_bundle_hash, evidence_valid=evidence_valid, reason=reason, as_of=as_of, known_as_of=known_as_of)

    def apply_conflict_verdict(self, *, principal: str, verdict: dict[str, Any], evidence_verification: dict[str, Any], review_state: dict[str, Any], action: str, reason: str) -> dict[str, Any]:
        return self.conflict_reviews.apply_verdict(principal=principal, verdict=verdict, evidence_verification=evidence_verification, review_state=review_state, action=action, reason=reason)

    def promote_learning_candidate(self, *, principal: str, reviewer: str, memory_id: str, evidence_verification: dict[str, Any], evidence_bundle_hash: str, confidence: dict[str, Any], confidence_snapshot: dict[str, Any]) -> dict[str, Any]:
        return self.conflict_reviews.promote_learning_candidate(principal=principal, reviewer=reviewer, memory_id=memory_id, evidence_verification=evidence_verification, evidence_bundle_hash=evidence_bundle_hash, confidence=confidence, confidence_snapshot=confidence_snapshot)

    def review_case_auto_advance(self, *, case_id: str, evidence_verification: Mapping[str, Any], actor: str = "system") -> dict[str, Any]:
        return self.review_lifecycle.auto_advance_after_evidence(case_id, evidence_verification=evidence_verification, actor=actor).as_dict()

    def record_review_decision(self, *, case_id: str, decision: str, actor: str, reason: str) -> dict[str, Any]:
        return self.review_lifecycle.record_decision(case_id, decision=decision, actor=actor, reason=reason)

    def close_review_case(self, *, case_id: str, actor: str, reason: str) -> dict[str, Any]:
        return self.review_lifecycle.close(case_id, actor=actor, reason=reason)

    def process_intent(self, intent_text: str) -> dict[str, Any]:
        return self.executive.process_as_ai_agent(intent_text)

    def new_session(self, goal: str = "") -> CognitiveSession:
        return self.sessions.create(goal)

    def save_session(self, session: CognitiveSession) -> str:
        return str(self.sessions.save(session))

    def resume_session(self, session_id: str) -> SessionResumeResult:
        return self.sessions.resume(session_id)

    def reflect_and_learn(self, *, goal: str, expected: str, observation: Mapping[str, Any], evidence_ids: tuple[str, ...] = ()) -> tuple[ReflectionResult, Any]:
        return self.learning.learn(goal=goal, expected=expected, observation=observation, evidence_ids=evidence_ids)

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
