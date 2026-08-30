"""Windows desktop identity binding for reviewer workflows."""

from __future__ import annotations

import getpass
import os
import platform
from dataclasses import dataclass
from typing import Mapping

from .reviewer_identity import ReviewerIdentity


@dataclass(frozen=True)
class WindowsIdentityProvider:
    """Resolve the local Windows session identity without assigning admin role."""

    admin_subjects: frozenset[str] = frozenset()

    def resolve(self) -> ReviewerIdentity:
        system = platform.system()
        if system != "Windows":
            return ReviewerIdentity(
                subject="",
                principal="UNAUTHENTICATED",
                authenticated=False,
                can_decide=False,
            )

        subject = self._subject()
        if not subject:
            return ReviewerIdentity(
                subject="",
                principal="UNAUTHENTICATED",
                authenticated=False,
                can_decide=False,
            )

        principal = "ADMIN" if subject in self.admin_subjects else "HUMAN"
        return ReviewerIdentity(
            subject=subject,
            principal=principal,
            authenticated=True,
            can_decide=True,
        )

    @staticmethod
    def _subject() -> str:
        for value in (
            os.environ.get("USERDOMAIN\\\\USERNAME"),
            os.environ.get("USERDOMAIN") and os.environ.get("USERNAME") and f"{os.environ['USERDOMAIN']}\\{os.environ['USERNAME']}",
            os.environ.get("USERNAME"),
        ):
            if value:
                return value.strip()
        try:
            value = getpass.getuser()
        except Exception:
            return ""
        return str(value).strip()
