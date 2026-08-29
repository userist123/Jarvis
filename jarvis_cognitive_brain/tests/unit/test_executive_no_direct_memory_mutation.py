from __future__ import annotations

from types import SimpleNamespace

from jarvis.core.executive import CognitiveExecutive


class RecordingGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.executive = SimpleNamespace(propose_synapse=self.propose_synapse)

    def propose_synapse(self, source_id: str, target_id: str):
        self.calls.append((source_id, target_id))
        return source_id


class FailingStorage:
    def update(self, *args, **kwargs):
        raise AssertionError("direct storage mutation must not be used for canonical synapses")


def test_fire_synapses_uses_canonical_executive_boundary() -> None:
    gateway = RecordingGateway()
    executive = CognitiveExecutive.__new__(CognitiveExecutive)
    executive.gateway = gateway
    executive.storage = FailingStorage()

    executive._fire_synapses([
        {"id": "memory-a"},
        {"id": "memory-b"},
    ])

    assert gateway.calls == [("memory-a", "memory-b")]
