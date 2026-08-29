from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

from jarvis.config import Settings, get_settings
from jarvis.core.cognitive_gateway import CognitiveGateway
from jarvis.llm.ollama_provider import OllamaProvider


@dataclass(frozen=True)
class RuntimeStatus:
    provider: str
    ollama_url: str
    ollama_healthy: bool
    model: str
    vault_path: str
    vault_present: bool
    executive_available: bool
    executive_reason: str
    vault_bridge_available: bool
    vault_bridge_reason: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


async def diagnose(settings: Settings | None = None) -> RuntimeStatus:
    """Return local runtime readiness without executing a user task."""
    cfg = settings or get_settings()
    provider = OllamaProvider(
        host=cfg.ollama_url,
        model=cfg.ollama_model,
        timeout=cfg.ollama_timeout,
    )
    ollama_healthy = await provider.health()
    gateway = CognitiveGateway(settings=cfg)

    vault_path = Path(cfg.vault_path).expanduser().resolve()
    bridge_status = gateway.vault_bridge.status
    return RuntimeStatus(
        provider=cfg.llm_provider,
        ollama_url=cfg.ollama_url,
        ollama_healthy=ollama_healthy,
        model=cfg.ollama_model,
        vault_path=str(vault_path),
        vault_present=vault_path.is_dir(),
        executive_available=gateway.executive.available,
        executive_reason=gateway.executive.reason,
        vault_bridge_available=bridge_status.available,
        vault_bridge_reason=bridge_status.reason,
    )


def format_status(status: RuntimeStatus) -> str:
    rows = [
        ("provider", status.provider),
        ("ollama_url", status.ollama_url),
        ("ollama_healthy", str(status.ollama_healthy)),
        ("model", status.model),
        ("vault_path", status.vault_path),
        ("vault_present", str(status.vault_present)),
        ("executive_available", str(status.executive_available)),
        ("executive_reason", status.executive_reason),
        ("vault_bridge_available", str(status.vault_bridge_available)),
        ("vault_bridge_reason", status.vault_bridge_reason),
    ]
    return "\n".join(f"{key}: {value}" for key, value in rows)
