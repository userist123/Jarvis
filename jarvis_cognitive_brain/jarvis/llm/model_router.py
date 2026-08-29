"""Provider-neutral model routing for local-first JARVIS inference.

Agents request a capability (fast, reasoning, coding, vision, embedding)
rather than naming a concrete vendor/model. Ollama is the default provider.
Cloud providers can be added later without changing agent code.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

from jarvis.config import Settings, get_settings
from jarvis.llm.base import BaseLLMProvider
from jarvis.llm.ollama_provider import OllamaProvider


@dataclass(frozen=True)
class ModelRoute:
    """Concrete model selection for one cognitive capability."""

    capability: str
    provider: str
    model: str


class ModelRouter:
    """Resolve logical model capabilities to concrete local providers."""

    DEFAULT_CAPABILITIES: Mapping[str, str] = {
        "fast": "ollama_model",
        "reasoning": "ollama_model",
        "coding": "ollama_model",
        "vision": "ollama_model",
    }

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def resolve(self, capability: str = "reasoning") -> ModelRoute:
        capability = capability.strip().lower() or "reasoning"
        model_field = self.DEFAULT_CAPABILITIES.get(capability, "ollama_model")
        model = getattr(self.settings, model_field)
        return ModelRoute(capability=capability, provider=self.settings.llm_provider, model=model)

    def provider(self, capability: str = "reasoning") -> BaseLLMProvider:
        route = self.resolve(capability)
        if route.provider != "ollama":
            raise RuntimeError(
                f"Provider '{route.provider}' is configured but no cloud adapter is active yet. "
                "JARVIS is intentionally local-first."
            )
        return OllamaProvider(
            host=self.settings.ollama_url,
            model=route.model,
            timeout=self.settings.ollama_timeout,
        )
