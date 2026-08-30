from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Mapping


def _parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class TemporalQuery:
    """Two-axis time query.

    ``as_of`` answers when the fact is valid. ``known_as_of`` answers what the
    system could have known by that date (knowledge time / extraction date).
    """

    as_of: date | None = None
    known_as_of: date | None = None

    @classmethod
    def from_values(cls, as_of: Any = None, known_as_of: Any = None) -> "TemporalQuery":
        return cls(_parse_date(as_of), _parse_date(known_as_of))


def matches_temporal(note: Mapping[str, Any], query: TemporalQuery) -> bool:
    """Return whether a note is valid and knowable at the requested times."""
    if query.as_of is not None:
        valid_from = _parse_date(note.get("valid_from"))
        valid_until = _parse_date(note.get("valid_until"))
        if valid_from is not None and query.as_of < valid_from:
            return False
        if valid_until is not None and query.as_of > valid_until:
            return False

    if query.known_as_of is not None:
        provenance = note.get("provenance") or {}
        extraction_date = _parse_date(provenance.get("extraction_date"))
        if extraction_date is not None and extraction_date > query.known_as_of:
            return False

    return True


def filter_temporal(notes: list[Mapping[str, Any]], query: TemporalQuery) -> list[Mapping[str, Any]]:
    return [note for note in notes if matches_temporal(note, query)]
