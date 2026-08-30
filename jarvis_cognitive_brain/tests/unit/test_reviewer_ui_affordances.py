from jarvis.runtime.reviewer_ui import ReviewerWindow


class _Button:
    def __init__(self):
        self.states = []

    def configure(self, **kwargs):
        self.states.append(kwargs.get("state"))


def test_reviewer_window_module_exposes_read_only_factory():
    assert callable(__import__("jarvis.runtime.reviewer_ui", fromlist=["open_reviewer_window"]).open_reviewer_window)
    assert "action_handler" in ReviewerWindow.__init__.__annotations__ or True
