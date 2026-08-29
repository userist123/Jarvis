import pytest

from jarvis.core.tool_executor import ApprovalRequiredError, RiskLevel, ToolExecutor, ToolSpec


class Policy:
    def __init__(self, allowed):
        self.allowed = set(allowed)

    def is_allowed(self, capability):
        return capability in self.allowed


def test_denied_capability_does_not_execute():
    called = []
    executor = ToolExecutor(Policy(set()))
    executor.register(ToolSpec("shell", "execute_code", RiskLevel.LOW, lambda: called.append(True)))

    observation = executor.execute("shell")

    assert observation.success is False
    assert "Capability denied" in observation.error
    assert called == []


def test_high_risk_requires_approval():
    executor = ToolExecutor(Policy({"network"}))
    executor.register(ToolSpec("fetch", "network", RiskLevel.HIGH, lambda: "ok"))

    with pytest.raises(ApprovalRequiredError):
        executor.execute("fetch")


def test_approved_tool_returns_observation():
    executor = ToolExecutor(Policy({"network"}))
    executor.register(ToolSpec("fetch", "network", RiskLevel.HIGH, lambda url: {"url": url}))

    observation = executor.execute("fetch", {"url": "http://localhost"}, approved=True)

    assert observation.success is True
    assert observation.result == {"url": "http://localhost"}
