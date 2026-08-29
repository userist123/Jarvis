"""Provider abstractions for JARVIS LLM backends."""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Generic, List, Dict, Optional, Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class CancellationError(asyncio.CancelledError):
    """Raised when a provider call is cancelled."""


class ProviderUnavailableError(RuntimeError):
    """Raised when an LLM provider cannot be reached."""


class CancellationToken:
    def __init__(self) -> None:
        self._event = asyncio.Event()

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise CancellationError()


class BaseLLMProvider(Generic[T]):
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, cancellation_token: Optional[CancellationToken] = None, **kwargs: Any) -> str:
        raise NotImplementedError

    async def chat(self, messages: List[Dict[str, str]], cancellation_token: Optional[CancellationToken] = None, **kwargs: Any) -> str:
        raise NotImplementedError

    async def stream(self, prompt: str, system_prompt: Optional[str] = None, cancellation_token: Optional[CancellationToken] = None, **kwargs: Any) -> AsyncIterator[str]:
        raise NotImplementedError

    async def structured(self, prompt: str, schema: Type[T], system_prompt: Optional[str] = None, cancellation_token: Optional[CancellationToken] = None, **kwargs: Any) -> T:
        raw = await self.generate(prompt, system_prompt=system_prompt, cancellation_token=cancellation_token, format="json", **kwargs)
        return schema.model_validate_json(raw)
