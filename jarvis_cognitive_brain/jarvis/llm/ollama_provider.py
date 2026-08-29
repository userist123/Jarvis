"""Async Ollama provider for local-first JARVIS inference."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, List, Optional, Type

import httpx
from pydantic import BaseModel

from jarvis.llm.base import BaseLLMProvider, CancellationError, CancellationToken, ProviderUnavailableError, T


class OllamaProvider(BaseLLMProvider):
    """Call a local Ollama daemon through its REST API."""

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "qwen2.5-coder:7b",
        timeout: float = 30.0,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self.host = host.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._external_client = client

    def _get_client(self) -> httpx.AsyncClient:
        return self._external_client or httpx.AsyncClient(timeout=self.timeout)

    async def health(self) -> bool:
        client = self._get_client()
        close = self._external_client is None
        try:
            response = await client.get(f"{self.host}/api/tags")
            response.raise_for_status()
            return True
        except (httpx.HTTPError, OSError):
            return False
        finally:
            if close:
                await client.aclose()

    async def generate(self, prompt: str, system_prompt: Optional[str] = None, cancellation_token: Optional[CancellationToken] = None, **kwargs: Any) -> str:
        if cancellation_token:
            cancellation_token.raise_if_cancelled()
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "options": kwargs.get("options", {}),
        }
        if "format" in kwargs:
            payload["format"] = kwargs["format"]
        client = self._get_client()
        close = self._external_client is None
        try:
            response = await client.post(f"{self.host}/api/generate", json=payload)
            response.raise_for_status()
            return str(response.json().get("response", ""))
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ProviderUnavailableError(f"Ollama provider at {self.host} unavailable: {exc}") from exc
        except CancellationError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Ollama generation failed: {exc}") from exc
        finally:
            if close:
                await client.aclose()

    async def chat(self, messages: List[Dict[str, str]], cancellation_token: Optional[CancellationToken] = None, **kwargs: Any) -> str:
        if cancellation_token:
            cancellation_token.raise_if_cancelled()
        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": kwargs.get("options", {}),
        }
        if "format" in kwargs:
            payload["format"] = kwargs["format"]
        client = self._get_client()
        close = self._external_client is None
        try:
            response = await client.post(f"{self.host}/api/chat", json=payload)
            response.raise_for_status()
            return str(response.json().get("message", {}).get("content", ""))
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ProviderUnavailableError(f"Ollama provider at {self.host} unavailable: {exc}") from exc
        except CancellationError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Ollama chat failed: {exc}") from exc
        finally:
            if close:
                await client.aclose()

    async def stream(self, prompt: str, system_prompt: Optional[str] = None, cancellation_token: Optional[CancellationToken] = None, **kwargs: Any) -> AsyncIterator[str]:
        if cancellation_token:
            cancellation_token.raise_if_cancelled()
        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": True,
            "options": kwargs.get("options", {}),
        }
        client = self._get_client()
        close = self._external_client is None
        try:
            async with client.stream("POST", f"{self.host}/api/generate", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if cancellation_token:
                        cancellation_token.raise_if_cancelled()
                    if not line:
                        continue
                    data = json.loads(line)
                    token = data.get("response")
                    if token:
                        yield str(token)
                    if data.get("done"):
                        break
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            raise ProviderUnavailableError(f"Ollama provider at {self.host} unavailable: {exc}") from exc
        except CancellationError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Ollama streaming failed: {exc}") from exc
        finally:
            if close:
                await client.aclose()

    async def structured(self, prompt: str, schema: Type[T], system_prompt: Optional[str] = None, cancellation_token: Optional[CancellationToken] = None, **kwargs: Any) -> T:
        return await super().structured(prompt, schema, system_prompt=system_prompt, cancellation_token=cancellation_token, **kwargs)
