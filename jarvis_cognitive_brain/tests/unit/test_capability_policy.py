import pytest

from jarvis.core.capability_policy import Capability, CapabilityPolicy


def test_memory_read_and_write_are_allowed():
    policy = CapabilityPolicy()
    assert policy.decide(Capability.READ_MEMORY).allowed
    assert policy.decide(Capability.WRITE_MEMORY).allowed


def test_sensitive_capabilities_are_denied_by_default():
    policy = CapabilityPolicy()
    assert not policy.decide(Capability.IOT_CONTROL).allowed
    assert not policy.decide(Capability.EXECUTE_CODE).allowed
    assert not policy.decide(Capability.NETWORK).allowed


def test_require_raises_for_denied_capability():
    policy = CapabilityPolicy()
    with pytest.raises(PermissionError):
        policy.require(Capability.EXECUTE_CODE)
