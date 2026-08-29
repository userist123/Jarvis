"""Provider-neutral capability routing for local-first JARVIS inference."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from jarvis.config import Settings, get_settings
from jarvis.llm.base import BaseLLMProvider
from jarvis.llm.ollama_provider import OllamaProvider


@dataclass(frozen=True)
class ModelRoute:
    capability: str
    provider: str
    model: str


class ModelRouter:
    """Resolve logical capabilities to concrete local Ollama models."""

    _MODEL_FIELDS = {
        "fast": "ollama_fast_model",
        "reasoning": "ollama_reasoning_model",
        "coding": "ollama_coding_model",
        "vision": "ollama_vision_model",
    }

    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()

    def resolve(self, capability: str = "reasoning") -> ModelRoute:
        capability = (capability or "reasoning").strip().lower()
        field = self._MODEL_FIELDS.get(capability)
        configured = getattr(self.settings, field, "") if field else ""
        model = configured.strip() or self.settings.ollama_model
        return ModelRoute(capability=capability, provider=self.settings.llm_provider, model=model)

    def provider(self, capability: str = "reasoning") -> BaseLLMProvider:
        route = self.resolve(capability)
        if route.provider != "ollama":
            raise RuntimeError(
                f"Provider '{route.provider}' is configured but has no active adapter. "
                "JARVIS remains local-first until an optional cloud adapter is enabled."
            )
        return OllamaProvider(
            host=self.settings.ollama_url,
            model=route.model,
            timeout=self.settings.ollama_timeout,
        )
