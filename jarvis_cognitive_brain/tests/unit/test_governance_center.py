from jarvis.runtime.governance_center import GovernanceCenterService


class LearningStore:
    def records(self):
        return []


class ReviewStates:
    def all(self):
        return [
            {"case_id": "CR-1", "state": "DECISION_PENDING", "can_apply_mutation": False},
            {"case_id": "CR-2", "state": "APPROVED", "can_apply_mutation": True},
        ]


class Dashboard:
    pass


def test_governance_center_is_read_only_and_exposes_identity():
    service = GovernanceCenterService(LearningStore(), ReviewStates())
    result = service.build(identity={"subject": "DOMAIN\\alice", "principal": "HUMAN", "authenticated": True})
    payload = result.as_dict()

    assert payload["read_only"] is True
    assert payload["identity"]["subject"] == "DOMAIN\\alice"
    assert payload["conflicts"]["total_cases"] == 2
    assert payload["pending_actions"][0]["case_id"] == "CR-1"
    assert payload["pending_actions"][0]["can_apply_mutation"] is False
