from jarvis.runtime.reviewer_identity import ReviewerPrincipal
from jarvis.runtime.windows_identity import WindowsIdentityProvider


def test_non_windows_is_unauthenticated(monkeypatch):
    monkeypatch.setattr("jarvis.runtime.windows_identity.platform.system", lambda: "Linux")
    identity = WindowsIdentityProvider().resolve()
    assert identity.principal == ReviewerPrincipal.UNAUTHENTICATED
    assert identity.authenticated is False
    assert identity.can_decide is False


def test_windows_user_maps_to_human(monkeypatch):
    monkeypatch.setattr("jarvis.runtime.windows_identity.platform.system", lambda: "Windows")
    monkeypatch.setenv("USERDOMAIN", "DOMAIN")
    monkeypatch.setenv("USERNAME", "alice")
    identity = WindowsIdentityProvider().resolve()
    assert identity.subject == r"DOMAIN\alice"
    assert identity.principal == ReviewerPrincipal.HUMAN
    assert identity.can_decide is True


def test_explicit_admin_allowlist_maps_to_admin(monkeypatch):
    monkeypatch.setattr("jarvis.runtime.windows_identity.platform.system", lambda: "Windows")
    monkeypatch.setenv("USERDOMAIN", "DOMAIN")
    monkeypatch.setenv("USERNAME", "admin")
    identity = WindowsIdentityProvider(admin_subjects=frozenset({r"DOMAIN\admin"})).resolve()
    assert identity.principal == ReviewerPrincipal.ADMIN
    assert identity.can_decide is True
