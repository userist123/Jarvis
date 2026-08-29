"""Deterministic capability-based agent routing for JARVIS.

The router ranks agent profiles using task signals and keeps provider/model
selection separate from agent selection.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Mapping


@dataclass(frozen=True)
class AgentProfile:
    name: str
    capabilities: tuple[str, ...]
    keywords: tuple[str, ...] = ()
    priority: float = 0.0
    enabled: bool = True


@dataclass(frozen=True)
class AgentRoute:
    agent: str
    score: float
    matched_capabilities: tuple[str, ...]
    matched_keywords: tuple[str, ...]
    reason: str


def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[\w.-]+", value.casefold()))


class AgentRouter:
    """Select the best enabled agent for a task without invoking an LLM."""

    def __init__(self, profiles: Iterable[AgentProfile] = ()) -> None:
        self._profiles = list(profiles)

    def add_profile(self, profile: AgentProfile) -> None:
        self._profiles.append(profile)

    def route(self, task: str, required_capabilities: Iterable[str] = ()) -> AgentRoute | None:
        query_tokens = _tokens(task)
        required = {str(c).casefold() for c in required_capabilities}
        ranked: list[AgentRoute] = []

        for profile in self._profiles:
            if not profile.enabled:
                continue
            caps = {c.casefold() for c in profile.capabilities}
            keywords = {k.casefold() for k in profile.keywords}
            matched_caps = tuple(sorted(required & caps))
            if required and not required.issubset(caps):
                continue
            matched_keywords = tuple(sorted(k for k in keywords if k in query_tokens))
            score = profile.priority + (0.65 * len(matched_caps)) + (0.20 * len(matched_keywords))
            if not required and not matched_keywords and not profile.priority:
                continue
            ranked.append(
                AgentRoute(
                    agent=profile.name,
                    score=score,
                    matched_capabilities=matched_caps,
                    matched_keywords=matched_keywords,
                    reason=f"capabilities={len(matched_caps)}, keywords={len(matched_keywords)}, priority={profile.priority:.2f}",
                )
            )

        if not ranked:
            return None
        ranked.sort(key=lambda item: (-item.score, item.agent))
        return ranked[0]

    def rank(self, task: str, required_capabilities: Iterable[str] = ()) -> list[AgentRoute]:
        query_tokens = _tokens(task)
        required = {str(c).casefold() for c in required_capabilities}
        ranked: list[AgentRoute] = []
        for profile in self._profiles:
            if not profile.enabled:
                continue
            caps = {c.casefold() for c in profile.capabilities}
            if required and not required.issubset(caps):
                continue
            keyword_matches = tuple(sorted(k.casefold() for k in profile.keywords if k.casefold() in query_tokens))
            cap_matches = tuple(sorted(required & caps))
            score = profile.priority + (0.65 * len(cap_matches)) + (0.20 * len(keyword_matches))
            ranked.append(AgentRoute(profile.name, score, cap_matches, keyword_matches,
                                     f"capabilities={len(cap_matches)}, keywords={len(keyword_matches)}, priority={profile.priority:.2f}"))
        return sorted(ranked, key=lambda item: (-item.score, item.agent))
