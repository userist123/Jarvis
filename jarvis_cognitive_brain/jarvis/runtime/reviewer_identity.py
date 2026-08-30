"""Explicit reviewer identity context for JARVIS review workflows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ReviewerPrincipal(str, Enum):
    UNAUTHENTICATED = "UNAUTHENTICATED"
    HUMAN = "HUMAN"
    ADMIN = "ADMIN"
    AI_AGENT = "AI_AGENT"


@dataclass(frozen=True)
class ReviewerIdentity:
    """Identity supplied by an authenticated host, not by review controls."""

    subject: str
    principal: ReviewerPrincipal
    authenticated: bool

    @classmethod
    def unauthenticated(cls) -> "ReviewerIdentity":
        return cls(subject="", principal=ReviewerPrincipal.UNAUTHENTICATED, authenticated=False)

    @property
    def can_decide(self) -> bool:
        return self.authenticated and self.principal in {
            ReviewerPrincipal.HUMAN,
            ReviewerPrincipal.ADMIN,
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "subject": self.subject,
            "principal": self.principal.value,
            "authenticated": self.authenticated,
            "can_decide": self.can_decide,
        }
