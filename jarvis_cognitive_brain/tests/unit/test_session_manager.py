from jarvis.config import Settings
from jarvis.core.session_manager import SessionManager


def test_session_manager_create_save_resume(tmp_path):
    settings = Settings(checkpoint_dir=tmp_path)
    manager = SessionManager(settings)

    session = manager.create("test goal")
    session.record_activation("note-1", 0.8)
    session.plan_id = "plan-1"
    session.tick = 3
    manager.save(session)

    resumed = manager.resume(session.session_id)
    assert resumed.resumed is True
    assert resumed.session.goal == "test goal"
    assert resumed.session.active_nodes == [{"id": "note-1", "activation": 0.8}]
    assert resumed.session.plan_id == "plan-1"
    assert resumed.session.tick == 3


def test_session_manager_missing_session(tmp_path):
    manager = SessionManager(Settings(checkpoint_dir=tmp_path))
    result = manager.resume("missing")
    assert result.resumed is False
    assert result.session.session_id == "missing"
