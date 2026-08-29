from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Mapping, Optional


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ApprovalRequiredError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolSpec:
    name: str
    capability: str
    risk: RiskLevel = RiskLevel.LOW
    handler: Optional[Callable[..., Any]] = None


@dataclass(frozen=True)
class ToolObservation:
    tool: str
    success: bool
    result: Any = None
    error: str = ""


class ToolExecutor:
    """Guarded side-effect boundary for JARVIS tools."""

    def __init__(self, policy: Any) -> None:
        self.policy = policy
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if spec.name in self._tools:
            raise ValueError(f"Tool already registered: {spec.name}")
        if spec.handler is None:
            raise ValueError("Tool handler is required")
        self._tools[spec.name] = spec

    def get(self, name: str) -> ToolSpec:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool: {name}") from exc

    def execute(
        self,
        name: str,
        args: Optional[Mapping[str, Any]] = None,
        *,
        approved: bool = False,
    ) -> ToolObservation:
        spec = self.get(name)
        allowed = bool(self.policy.is_allowed(spec.capability))
        if not allowed:
            return ToolObservation(name, False, error=f"Capability denied: {spec.capability}")

        if spec.risk in (RiskLevel.HIGH, RiskLevel.CRITICAL) and not approved:
            raise ApprovalRequiredError(f"Approval required for {name} ({spec.risk.value})")

        try:
            result = spec.handler(**dict(args or {}))
            return ToolObservation(name, True, result=result)
        except Exception as exc:
            return ToolObservation(name, False, error=f"{exc.__class__.__name__}: {exc}")

    @property
    def registered_tools(self) -> tuple[str, ...]:
        return tuple(sorted(self._tools))
