from jarvis.runtime.unified_case_lifecycle import CaseStatus, can_apply_mutation, validate_transition
from jarvis.runtime.unified_case_adapter import from_learning, from_memory_case


def test_automated_transitions_stop_before_decision():
    validate_transition(CaseStatus.OPEN, CaseStatus.EVIDENCE_PENDING, automated=True)
    validate_transition(CaseStatus.EVIDENCE_PENDING, CaseStatus.VERIFIED, automated=True)
    validate_transition(CaseStatus.VERIFIED, CaseStatus.DECISION_PENDING, automated=True)
    try:
        validate_transition(CaseStatus.DECISION_PENDING, CaseStatus.APPROVED, automated=True)
    except ValueError:
        pass
    else:
        raise AssertionError("automated flow must not approve")


def test_mutation_requires_approved():
    assert not can_apply_mutation(CaseStatus.DECISION_PENDING, action="attest")
    assert not can_apply_mutation(CaseStatus.DEFERRED, action="attest")
    assert can_apply_mutation(CaseStatus.APPROVED, action="attest")


def test_learning_adapter_is_unified():
    case = from_learning({"case_id": "MC-1", "signal_id": "sig-1", "route": "LEARNING_REVIEW", "status": "OPEN"})
    assert case.kind == "learning"
    assert case.status is CaseStatus.OPEN


def test_provisional_adapter_handles_unknown_state():
    case = from_memory_case({"case_id": "MC-2", "kind": "memory", "route": "MEMORY_REVIEW", "status": "UNKNOWN"})
    assert case.status is CaseStatus.OPEN
