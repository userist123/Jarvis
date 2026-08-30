"""Windows desktop identity binding for reviewer workflows."""

from __future__ import annotations

import getpass
import os
import platform
from dataclasses import dataclass

from .reviewer_identity import ReviewerIdentity, ReviewerPrincipal


@dataclass(frozen=True)
class WindowsIdentityProvider:
    """Resolve the local Windows session identity without assigning admin role automatically."""

    admin_subjects: frozenset[str] = frozenset()

    def resolve(self) -> ReviewerIdentity:
        if platform.system() != "Windows":
            return ReviewerIdentity.unauthenticated()
        subject = self._subject()
        if not subject:
            return ReviewerIdentity.unauthenticated()
        principal = ReviewerPrincipal.ADMIN if subject in self.admin_subjects else ReviewerPrincipal.HUMAN
        return ReviewerIdentity(subject=subject, principal=principal, authenticated=True)

    @staticmethod
    def _subject() -> str:
        domain = os.environ.get("USERDOMAIN", "").strip()
        username = os.environ.get("USERNAME", "").strip()
        if domain and username:
            return f"{domain}\\{username}"
        if username:
            return username
        try:
            return str(getpass.getuser()).strip()
        except Exception:
            return ""
