"""
Complete Stateful OODA Cognitive Loop: Observe, Retrieve, Reason, Plan, Act, Reflect, Consolidate.
"""

import time
import uuid
from typing import List, Dict, Any, Optional, Callable, Union

from jarvis.llm.base import BaseLLMProvider
from jarvis.memory.sqlite_engine import SQLiteStorageEngine
from jarvis.memory.recall import MultiSignalRecallEngine
from jarvis.memory.reflection import ReflexionEngine
from jarvis.memory.consolidation import ConsolidationEngine
from jarvis.memory.memory_governance import MemoryGovernance
from jarvis.memory.retrieval_ranker import RetrievalRanker
from jarvis.memory.invariants import Principal, Lifecycle, NoteType
from jarvis.core.models import (
    PerceptionEvent, UserIntent, IntentType, WorkingMemory, ActivePlan,
    PlanStep, StepStatus, StepExecutionResult, OODACycleResult,
)
from jarvis.core.cognitive_gateway import CognitiveGateway
from jarvis.core.capability_policy import Capability, CapabilityPolicy


class OODACognitiveEngine:
    """Stateful OODA loop executing discrete cognitive cycles."""

    def __init__(self, llm_provider: Optional[BaseLLMProvider], storage_engine: SQLiteStorageEngine,
                 working_memory_capacity: int = 10,
                 tool_executor: Optional[Callable[[str, Dict[str, Any]], Any]] = None,
                 cognitive_gateway: Optional[CognitiveGateway] = None,
                 capability_policy: Optional[CapabilityPolicy] = None,
                 memory_governance: Optional[MemoryGovernance] = None,
                 retrieval_ranker: Optional[RetrievalRanker] = None):
        self.storage = storage_engine
        self.recall_engine = MultiSignalRecallEngine(self.storage)
        self.reflexion = ReflexionEngine(self.storage)
        self.consolidator = ConsolidationEngine(self.storage)
        self.memory_governance = memory_governance or MemoryGovernance()
        self.retrieval_ranker = retrieval_ranker or RetrievalRanker()
        self.working_memory = WorkingMemory(capacity=working_memory_capacity)
        self.tool_executor = tool_executor
        self.gateway = cognitive_gateway or CognitiveGateway(provider=llm_provider)
        self.llm = llm_provider or self.gateway.provider("reasoning")
        self.policy = capability_policy or CapabilityPolicy()

    async def observe(self, perception: PerceptionEvent) -> UserIntent:
        text = perception.raw_data.strip()
        lowered = text.lower()
        if any(w in lowered for w in ["turn on", "turn off", "set brightness", "set temperature", "light", "switch"]):
            intent_type, requires_tool = IntentType.IOT_CONTROL, True
        elif any(w in lowered for w in ["remember", "store note", "save memory", "keep note"]):
            intent_type, requires_tool = IntentType.MEMORY_STORE, True
        elif any(w in lowered for w in ["status", "system health", "cpu", "diagnostic"]):
            intent_type, requires_tool = IntentType.SYSTEM_STATUS, False
        elif any(w in lowered for w in ["plan", "step by step", "execute task", "workflow"]):
            intent_type, requires_tool = IntentType.TASK, True
        elif any(w in lowered for w in ["what", "how", "who", "when", "why", "search", "lookup", "find", "explain"]):
            intent_type, requires_tool = IntentType.QUERY, False
        else:
            intent_type, requires_tool = IntentType.CONVERSATION, False
        return UserIntent(raw_text=text, intent_type=intent_type, requires_tool=requires_tool, extracted_query=text, confidence=0.95)

    async def retrieve(self, intent: UserIntent) -> List[Dict[str, Any]]:
        query = intent.extracted_query or intent.raw_text
        active = self.working_memory.get_active_context()
        recalled = self.recall_engine.retrieve(query=query, working_memory_context=active, limit=max(self.working_memory.capacity * 3, 20))
        ranked = self.retrieval_ranker.rank(query, recalled, limit=max(self.working_memory.capacity * 2, 10))

        admitted: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()
        for note, score in ranked:
            note_copy = dict(note)
            note_id = str(note_copy.get("id") or "")
            if note_id and note_id in seen_ids:
                continue
            if note_id:
                seen_ids.add(note_id)
            note_copy["retrieval_score"] = round(score.final_score, 6)
            note_copy["retrieval_reason"] = score.reason
            admitted.append(note_copy)
            if len(admitted) >= self.working_memory.capacity:
                break

        self.working_memory.admit(admitted)
        return self.working_memory.get_active_context()

    async def reason_and_plan(self, intent: UserIntent, context: List[Dict[str, Any]]) -> ActivePlan:
        steps: List[PlanStep] = []
        if intent.intent_type == IntentType.QUERY:
            steps.append(PlanStep(step_id=1, action="synthesize_response", kwargs={"query": intent.raw_text, "context": context}, description="Synthesize knowledge-grounded answer using ranked recalled context"))
        elif intent.intent_type == IntentType.IOT_CONTROL:
            steps.append(PlanStep(step_id=1, action="iot_call", kwargs={"command": intent.raw_text}, description=f"Dispatch IoT Home Assistant control command: '{intent.raw_text}'"))
            steps.append(PlanStep(step_id=2, action="synthesize_response", kwargs={"query": f"Confirm execution of IoT command: {intent.raw_text}", "context": context}, description="Confirm device command completion"))
        elif intent.intent_type == IntentType.MEMORY_STORE:
            steps.append(PlanStep(step_id=1, action="propose_memory", kwargs={"raw_text": intent.raw_text, "context": context}, description="Govern, deduplicate, and propose note for canonical memory review"))
        else:
            steps.append(PlanStep(step_id=1, action="synthesize_response", kwargs={"query": intent.raw_text, "context": context}, description="Generate assistant conversational response"))
        return ActivePlan(goal=intent.raw_text, steps=steps)

    async def act_step(self, step: PlanStep, principal: Principal = Principal.AI_AGENT) -> StepExecutionResult:
        t0 = time.time()
        step.status = StepStatus.RUNNING
        try:
            if step.action == "synthesize_response":
                query = step.kwargs.get("query", "")
                ctx = step.kwargs.get("context", [])
                ctx_text = "\n\n".join([f"- Note [[{c.get('id', '')[:8]}]] (score={c.get('retrieval_score', 0):.3f}): {c.get('content', '')}" for c in ctx])
                system_prompt = (
                    "You are Jarvis, an advanced autonomous cognitive assistant. "
                    "Use the canonical AI Memory Vault operating contract and the relevant recalled memory. "
                    "Prefer higher-ranked evidence, respect confidence/provenance, and do not invent facts when verification is required."
                )
                prompt = f"User Request: {query}\n\nRanked Memory Context:\n{ctx_text}" if ctx_text else query
                response = await self.gateway.generate(prompt, capability="reasoning", system_prompt=system_prompt)
                res = {"answer": response, "memory_context_count": len(ctx)}
                step.status = StepStatus.SUCCESS
                step.result = res
                return StepExecutionResult(step_id=step.step_id, action=step.action, status="success", result=res, execution_time_ms=(time.time() - t0) * 1000.0)

            if step.action == "propose_memory":
                self.policy.require(Capability.WRITE_MEMORY)
                raw_text = step.kwargs.get("raw_text", "")
                existing = step.kwargs.get("context", [])
                note_id = str(uuid.uuid4())
                note_data = {"id": note_id, "type": NoteType.KNOWLEDGE.value, "lifecycle": Lifecycle.REVIEW.value,
                             "category": "user-memory", "tags": ["memory-store", "user-instruction"],
                             "created": time.strftime("%Y-%m-%d"), "updated": time.strftime("%Y-%m-%d"),
                             "provenance": {"source_type": "user", "source_ref": "ooda:memory-store"},
                             "confidence": "high", "verification": "unverified", "content": raw_text, "relations": []}
                decision = self.memory_governance.inspect_candidate(note_data, existing)
                if decision.action == "update":
                    res = {"status": "duplicate", "matched_id": decision.matched_id, "similarity": decision.similarity, "reason": decision.reason}
                elif decision.action == "reject":
                    raise ValueError(decision.reason)
                else:
                    self.storage.propose(principal, note_data)
                    res = {"note_id": note_id, "status": "review", "governance": decision.action, "reason": decision.reason,
                           "matched_id": decision.matched_id, "similarity": decision.similarity}
                step.status = StepStatus.SUCCESS
                step.result = res
                return StepExecutionResult(step_id=step.step_id, action=step.action, status="success", result=res, execution_time_ms=(time.time() - t0) * 1000.0)

            if step.action == "iot_call":
                self.policy.require(Capability.IOT_CONTROL)
                tool_res = self.tool_executor("iot_call", step.kwargs) if self.tool_executor else {"device": "home_assistant", "status": "executed", "command": step.kwargs.get("command")}
                step.status = StepStatus.SUCCESS
                step.result = tool_res
                return StepExecutionResult(step_id=step.step_id, action=step.action, status="success", result=tool_res, execution_time_ms=(time.time() - t0) * 1000.0)

            if self.tool_executor:
                self.policy.require(Capability.EXECUTE_CODE)
                tool_res = self.tool_executor(step.action, step.kwargs)
                step.status = StepStatus.SUCCESS
                step.result = tool_res
                return StepExecutionResult(step_id=step.step_id, action=step.action, status="success", result=tool_res, execution_time_ms=(time.time() - t0) * 1000.0)
            raise ValueError(f"Unknown action '{step.action}' and no custom tool_executor configured.")
        except Exception as exc:
            step.status = StepStatus.FAILED
            step.error = str(exc)
            return StepExecutionResult(step_id=step.step_id, action=step.action, status="error", error=str(exc), execution_time_ms=(time.time() - t0) * 1000.0)

    async def act(self, plan: ActivePlan, principal: Principal = Principal.AI_AGENT) -> List[StepExecutionResult]:
        results = []
        while not plan.is_complete():
            step = plan.get_next_step()
            if not step:
                break
            res = await self.act_step(step, principal=principal)
            results.append(res)
            if res.status == "success": plan.complete_current_step(res.result)
            else:
                plan.fail_current_step(res.error or "Unknown error")
                break
        return results

    async def reflect(self, target: Union[ActivePlan, PlanStep], error: Optional[str] = None, principal: Principal = Principal.AI_AGENT) -> Optional[str]:
        if isinstance(target, ActivePlan):
            failed_step = next((s for s in target.steps if s.status == StepStatus.FAILED), None)
            step_action = failed_step.action if failed_step else "plan_execution"
            err_msg = error or (failed_step.error if failed_step else "Plan execution failed")
        else:
            step_action = target.action
            err_msg = error or "Step execution failed"
        try:
            return self.reflexion.reflect_error(principal=principal, step_action=step_action, error_msg=err_msg)
        except Exception:
            return None

    async def consolidate(self, lesson_note: Optional[Dict[str, Any]] = None, principal: Principal = Principal.AI_AGENT) -> Optional[str]:
        if lesson_note:
            try:
                self.policy.require(Capability.WRITE_MEMORY)
                self.storage.propose(principal, lesson_note)
                return lesson_note.get("id")
            except Exception:
                return None
        try: return self.consolidator.consolidate_lessons(principal)
        except Exception: return None

    async def process_cycle(self, perception_or_text: Union[PerceptionEvent, str], principal: Principal = Principal.AI_AGENT, **kwargs: Any) -> OODACycleResult:
        perception = PerceptionEvent(channel="voice", raw_data=perception_or_text) if isinstance(perception_or_text, str) else perception_or_text
        return await self.execute_cycle(perception=perception, principal=principal, **kwargs)

    async def execute_cycle(self, perception: PerceptionEvent, principal: Principal = Principal.AI_AGENT, auto_checkpoint_callback: Optional[Callable[[], None]] = None) -> OODACycleResult:
        start_time = time.time()
        intent = await self.observe(perception)
        context = await self.retrieve(intent)
        plan = await self.reason_and_plan(intent, context)
        if auto_checkpoint_callback: auto_checkpoint_callback()
        step_results: List[StepExecutionResult] = []
        reflections: List[str] = []
        while not plan.is_complete():
            step = plan.get_next_step()
            if not step: break
            result = await self.act_step(step, principal=principal)
            step_results.append(result)
            if result.status == "success": plan.complete_current_step(result.result)
            else:
                plan.fail_current_step(result.error or "Unknown error")
                reflection_id = await self.reflect(step, result.error or "Unknown error", principal=principal)
                if reflection_id: reflections.append(reflection_id)
                break
            if auto_checkpoint_callback: auto_checkpoint_callback()
        consolidated_id = await self.consolidate(principal=principal)
        total_ms = (time.time() - start_time) * 1000.0
        return OODACycleResult(perception=perception, intent=intent, active_plan=plan, step_results=step_results,
                               context_used=context, reflections=reflections,
                               consolidated_ids=[consolidated_id] if consolidated_id else [], execution_time_ms=total_ms)