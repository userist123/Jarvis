"""
Cognitive Executive Daemon coordinating the OODA loop with atomic checkpointing and error recovery.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any, List, Union, Callable
import asyncio
from jarvis.llm.base import BaseLLMProvider
from jarvis.memory.sqlite_engine import SQLiteStorageEngine
from jarvis.memory.invariants import Principal
from jarvis.core.models import PerceptionEvent, WorkingMemory, ActivePlan, OODACycleResult
from jarvis.core.ooda import OODACognitiveEngine
from jarvis.core.cognitive_gateway import CognitiveGateway


class CognitiveExecutive:
    """Cognitive daemon coordinating OODA execution, checkpoints, and recovery."""

    def __init__(
        self,
        llm_provider: Optional[BaseLLMProvider],
        storage_engine: SQLiteStorageEngine,
        checkpoint_dir: Union[str, Path] = ".checkpoints",
        working_memory_capacity: int = 10,
        max_retries: int = 2,
        cognitive_gateway: Optional[CognitiveGateway] = None,
    ):
        self.checkpoint_dir = Path(checkpoint_dir)
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        self.max_retries = max_retries
        self.storage = storage_engine
        self.gateway = cognitive_gateway or CognitiveGateway(provider=llm_provider)
        self.engine = OODACognitiveEngine(
            llm_provider=llm_provider,
            storage_engine=storage_engine,
            working_memory_capacity=working_memory_capacity,
            cognitive_gateway=self.gateway,
        )
        self.working_memory: WorkingMemory = self.engine.working_memory
        self.active_plan: Optional[ActivePlan] = None
        self._state_callbacks: List[Callable[[dict], None]] = []

    def save_checkpoint(self) -> None:
        wm_file = self.checkpoint_dir / "wm.json"
        self.working_memory.save_state(wm_file)
        if self.active_plan:
            self.active_plan.save_state(self.checkpoint_dir / "plan.json")

    def load_checkpoint(self) -> bool:
        loaded = False
        wm_file = self.checkpoint_dir / "wm.json"
        if wm_file.exists():
            try:
                self.working_memory.load_state(wm_file)
                loaded = True
            except Exception:
                pass
        plan_file = self.checkpoint_dir / "plan.json"
        if plan_file.exists():
            try:
                self.active_plan = ActivePlan.load_state(plan_file)
                loaded = True
            except Exception:
                pass
        return loaded

    async def process_utterance(
        self,
        text: str,
        source: str = "voice",
        principal: Principal = Principal.AI_AGENT,
    ) -> OODACycleResult:
        perception = PerceptionEvent(channel=source, raw_data=text, metadata={"principal": principal.value})
        result = await self.engine.execute_cycle(
            perception=perception,
            principal=principal,
            auto_checkpoint_callback=self.save_checkpoint,
        )
        self.active_plan = result.active_plan
        self.save_checkpoint()
        if len(result.context_used) >= 2:
            self._fire_synapses(result.context_used)
        await self._emit_state({
            "active_plan_id": self.active_plan.id if self.active_plan else None,
            "memory_len": len(self.working_memory.entries),
            "principal": principal.value,
        })
        return result

    def _fire_synapses(self, context: List[Dict[str, Any]]) -> None:
        """Create co-activation edges only through the canonical Vault Executive."""
        for i in range(min(3, len(context) - 1)):
            node_a = context[i]
            node_b = context[i + 1]
            id_a = node_a.get("id")
            id_b = node_b.get("id")
            if not id_a or not id_b or id_a == id_b:
                continue
            try:
                self.gateway.executive.propose_synapse(str(id_a), str(id_b))
            except Exception:
                # Synapse creation is opportunistic and must never break the cycle.
                pass

    def register_state_callback(self, callback: Callable[[dict], None]) -> None:
        self._state_callbacks.append(callback)

    async def _emit_state(self, state: dict) -> None:
        for cb in list(self._state_callbacks):
            try:
                result = cb(state)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass
