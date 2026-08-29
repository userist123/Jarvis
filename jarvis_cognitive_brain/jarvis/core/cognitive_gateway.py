from __future__ import annotations

from typing import Any, Dict, Optional

from jarvis.config import Settings, get_settings
from jarvis.llm.base import BaseLLMProvider, CancellationToken
from jarvis.llm.model_router import ModelRouter
from jarvis.memory.vault_context import VaultContextLoader


class CognitiveGateway:
    """Single entry point for memory-grounded, provider-neutral reasoning."""

    def __init__(self, settings: Optional[Settings] = None, provider: Optional[BaseLLMProvider] = None) -> None:
        self.settings = settings or get_settings()
        self.router = ModelRouter(self.settings)
        self.vault = VaultContextLoader(settings=self.settings)
        self._provider_override = provider

    def provider(self, capability: str = "reasoning") -> BaseLLMProvider:
        return self._provider_override or self.router.provider(capability)

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
