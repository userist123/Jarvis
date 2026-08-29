"""Capability-based execution policy for the JARVIS runtime."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Optional


class Capability(str, Enum):
    READ_MEMORY = "read_memory"
    WRITE_MEMORY = "write_memory"
    IOT_CONTROL = "iot_control"
    EXECUTE_CODE = "execute_code"
    NETWORK = "network"


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    capability: Capability
    reason: str


class CapabilityPolicy:
    """Small deterministic policy gate independent from the LLM."""

    def __init__(self, grants: Optional[Mapping[Capability, bool]] = None) -> None:
        defaults = {
            Capability.READ_MEMORY: True,
            Capability.WRITE_MEMORY: True,
            Capability.IOT_CONTROL: False,
            Capability.EXECUTE_CODE: False,
            Capability.NETWORK: False,
        }
        if grants:
            defaults.update(grants)
        self._grants = defaults

    def decide(self, capability: Capability) -> PolicyDecision:
        allowed = bool(self._grants.get(capability, False))
        if allowed:
            return PolicyDecision(True, capability, "Capability granted by local policy.")
        return PolicyDecision(False, capability, "Capability is denied by local policy.")

    def require(self, capability: Capability) -> None:
        decision = self.decide(capability)
        if not decision.allowed:
            raise PermissionError(decision.reason)
