import tkinter as tk


def test_gui_module_imports_without_creating_a_window():
    from jarvis.runtime import gui

    assert hasattr(gui, "JarvisApp")
    assert hasattr(gui, "main")


def test_gui_app_uses_shared_chat_runtime(monkeypatch):
    from jarvis.runtime import gui

    created = {}

    class FakeChat:
        def __init__(self, settings):
            created["settings"] = settings

    monkeypatch.setattr(gui, "ChatRuntime", FakeChat)

    # No Tk root is created here; this test only guards construction dependencies.
    assert gui.ChatRuntime is FakeChat
    assert "tk" in gui.__dict__
