from jarvis.runtime.conflict_review import ConflictReviewService


class FakeBackend:
    controller = object()


class FakeBridge:
    available = True
    _backend = FakeBackend()


def test_conflict_review_service_opens_case_without_mutation(monkeypatch):
    monkeypatch.setattr(
        "memory_controller.conflict_review.ConflictReviewWorkflow",
        lambda: _WorkflowStub(),
        raising=False,
    )
    service = ConflictReviewService(FakeBridge())
    result = service.open_case(memory_ids=["a", "b"], reasons=["opposing assertions"])
    assert result["status"] == "OPEN"
    assert result["recommendation"] == "VERIFY_WITH_EVIDENCE"


class _WorkflowStub:
    class _Case:
        def as_dict(self):
            return {"case_id": "CR-test", "status": "OPEN", "recommendation": "VERIFY_WITH_EVIDENCE"}

    def open_case(self, **kwargs):
        return self._Case()
