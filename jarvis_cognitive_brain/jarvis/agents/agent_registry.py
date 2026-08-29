"""Filesystem-backed registry for agents and skills stored in the AI Memory Vault.

The registry stores only derived metadata in memory. It never copies full skill
instructions into JARVIS state, which keeps the Vault as the canonical source.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

from jarvis.agents.agent_router import AgentProfile


@dataclass(frozen=True)
class AgentArtifact:
    name: str
    root: Path
    briefing: Path | None
    dispatch: Path | None
    handoff: Path | None
    skills: tuple[Path, ...]
    archetype: str | None
    description: str


_FRONTMATTER = re.compile(r"^---\s*\n(?P<body>.*?)\n---\s*$", re.DOTALL)


def _frontmatter(text: str) -> dict[str, str]:
    match = _FRONTMATTER.match(text.strip())
    if not match:
        return {}
    values: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip().casefold()] = value.strip().strip("\"'")
    return values


class AgentRegistry:
    """Discover agent workspaces and global skills from the canonical vault."""

    def __init__(self, vault_root: str | Path) -> None:
        self.vault_root = Path(vault_root).expanduser().resolve()
        self.agents_root = self.vault_root / ".agents"
        self._artifacts: list[AgentArtifact] = []

    @property
    def artifacts(self) -> tuple[AgentArtifact, ...]:
        return tuple(self._artifacts)

    def discover(self) -> tuple[AgentArtifact, ...]:
        found: list[AgentArtifact] = []
        if not self.agents_root.is_dir():
            self._artifacts = []
            return ()

        for root in sorted(self.agents_root.iterdir(), key=lambda p: p.name.casefold()):
            if not root.is_dir() or root.name in {"skills", "_archive", "_system"}:
                continue
            briefing = root / "BRIEFING.md"
            dispatch = root / "DISPATCH.md"
            handoff = root / "handoff.md"
            skill_files = tuple(sorted(root.rglob("SKILL.md")))

            archetype: str | None = None
            description = root.name
            if briefing.is_file():
                meta = _frontmatter(briefing.read_text(encoding="utf-8", errors="replace"))
                archetype = meta.get("archetype")
                description = meta.get("target") or meta.get("mission") or description

            found.append(
                AgentArtifact(
                    name=root.name,
                    root=root,
                    briefing=briefing if briefing.is_file() else None,
                    dispatch=dispatch if dispatch.is_file() else None,
                    handoff=handoff if handoff.is_file() else None,
                    skills=skill_files,
                    archetype=archetype,
                    description=description,
                )
            )

        self._artifacts = found
        return tuple(found)

    def to_profiles(self, *, default_priority: float = 0.05) -> tuple[AgentProfile, ...]:
        if not self._artifacts:
            self.discover()
        profiles: list[AgentProfile] = []
        for artifact in self._artifacts:
            tokens: set[str] = set()
            if artifact.archetype:
                tokens.update(re.findall(r"[\w.-]+", artifact.archetype.casefold()))
            tokens.update(re.findall(r"[\w.-]+", artifact.description.casefold()))
            for skill in artifact.skills[:20]:
                tokens.update(re.findall(r"[\w.-]+", skill.parent.name.casefold()))
                tokens.update(re.findall(r"[\w.-]+", skill.stem.casefold()))
            capabilities = set(tokens)
            profiles.append(
                AgentProfile(
                    name=artifact.name,
                    capabilities=tuple(sorted(capabilities)),
                    keywords=tuple(sorted(tokens)),
                    priority=default_priority,
                )
            )
        return tuple(profiles)

    def build_router(self):
        from jarvis.agents.agent_router import AgentRouter

        return AgentRouter(self.to_profiles())
