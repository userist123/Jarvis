from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class EvidenceItem:
    note_id: str
    status: str
    provenance: Mapping[str, Any] = field(default_factory=dict)
    excerpt: str = ""


@dataclass(frozen=True)
class ExecutionFacts:
    status: str
    reason: str = ""
    result: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ContextPack:
    intent: str
    mode: str
    agents: tuple[str, ...] = ()
    evidence: tuple[EvidenceItem, ...] = ()
    execution: ExecutionFacts | None = None
    constraints: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        if self.execution is None:
            data["execution"] = None
        return data

    def to_prompt(self, max_chars: int = 12000) -> str:
        lines = [
            "GROUNDING CONTRACT:",
            f"intent={self.intent}",
            f"mode={self.mode}",
            f"agents={', '.join(self.agents) or 'none'}",
        ]
        if self.constraints:
            lines.append("constraints:")
            lines.extend(f"- {item}" for item in self.constraints)
        if self.execution:
            lines.append(
                f"execution.status={self.execution.status}; reason={self.execution.reason}"
            )
            if self.execution.result:
                lines.append(f"execution.result={dict(self.execution.result)}")
        if self.evidence:
            lines.append("evidence:")
            for item in self.evidence:
                provenance = dict(item.provenance)
                lines.append(
                    f"- id={item.note_id}; status={item.status}; "
                    f"provenance={provenance}; excerpt={item.excerpt[:500]}"
                )
        text = "\n".join(lines)
        return text[:max_chars]


def build_evidence(items: Sequence[Mapping[str, Any]]) -> tuple[EvidenceItem, ...]:
    result: list[EvidenceItem] = []
    for item in items:
        note_id = str(item.get("id", ""))
        if not note_id:
            continue
        result.append(
            EvidenceItem(
                note_id=note_id,
                status=str(item.get("evidence_status") or item.get("verification") or "unverified"),
                provenance=item.get("provenance") or {},
                excerpt=str(item.get("content") or item.get("snippet") or ""),
            )
        )
    return tuple(result)
