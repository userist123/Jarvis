"""Budgeted, auditable context assembly for memory-grounded reasoning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class AssembledContext:
    text: str
    note_ids: tuple[str, ...]
    characters: int
    truncated: bool


class ContextAssembler:
    """Build a bounded context block without allowing incidental memory to crowd out policy."""

    def __init__(self, *, max_chars: int = 12000, max_notes: int = 8) -> None:
        if max_chars < 256:
            raise ValueError("max_chars must be >= 256")
        if max_notes < 1:
            raise ValueError("max_notes must be >= 1")
        self.max_chars = max_chars
        self.max_notes = max_notes

    @staticmethod
    def _note_block(note: Mapping[str, Any]) -> str:
        note_id = str(note.get("id") or "unknown")
        note_type = str(note.get("type") or "memory")
        confidence = str(note.get("confidence") or "unknown")
        verification = str(note.get("verification") or "unknown")
        content = str(note.get("content") or "").strip()
        return (
            f"### Memory {note_id[:12]}\n"
            f"type={note_type}; confidence={confidence}; verification={verification}\n"
            f"{content}\n"
        )

    def assemble(self, notes: Sequence[Mapping[str, Any]]) -> AssembledContext:
        chunks: list[str] = []
        ids: list[str] = []
        used = 0
        truncated = False

        for note in notes[: self.max_notes]:
            block = self._note_block(note)
            if not block.strip():
                continue
            if used + len(block) <= self.max_chars:
                chunks.append(block)
                used += len(block)
                note_id = str(note.get("id") or "")
                if note_id:
                    ids.append(note_id)
                continue

            remaining = self.max_chars - used
            if remaining <= 0:
                truncated = True
                break
            chunks.append(block[:remaining].rstrip() + "\n")
            used += remaining
            truncated = True
            note_id = str(note.get("id") or "")
            if note_id:
                ids.append(note_id)
            break

        return AssembledContext(
            text="\n".join(chunks).strip(),
            note_ids=tuple(ids),
            characters=used,
            truncated=truncated,
        )
