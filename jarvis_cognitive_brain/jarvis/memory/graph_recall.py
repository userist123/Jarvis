"""Relation-aware memory expansion for JARVIS retrieval."""

from __future__ import annotations

from collections import deque
from typing import Any, Iterable, Mapping


_RELATION_WEIGHTS = {
    "supports": 1.00,
    "depends_on": 0.95,
    "replaces": 0.90,
    "derived_from": 0.85,
    "contradicts": 0.80,
    "co_activated": 0.65,
    "related_to": 0.55,
}


class GraphRecall:
    """Expand ranked memories through explicit relation edges without inventing links."""

    def __init__(self, *, max_hops: int = 1, relation_bonus: float = 0.12) -> None:
        if max_hops < 0:
            raise ValueError("max_hops must be >= 0")
        self.max_hops = max_hops
        self.relation_bonus = relation_bonus

    @staticmethod
    def _relations(note: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        relations = note.get("relations") or []
        return [r for r in relations if isinstance(r, Mapping)]

    @staticmethod
    def _target_id(relation: Mapping[str, Any]) -> str | None:
        value = relation.get("target_id") or relation.get("target")
        return str(value) if value else None

    def expand(
        self,
        seeds: Iterable[Mapping[str, Any]],
        candidates_by_id: Mapping[str, Mapping[str, Any]],
    ) -> list[dict[str, Any]]:
        """Return seed notes plus explicitly related notes, with bounded hop count."""
        result: dict[str, dict[str, Any]] = {}
        queue: deque[tuple[str, Mapping[str, Any], int, float]] = deque()

        for seed in seeds:
            note_id = str(seed.get("id") or "")
            if not note_id:
                continue
            item = dict(seed)
            item.setdefault("graph_bonus", 0.0)
            item.setdefault("graph_hops", 0)
            result[note_id] = item
            queue.append((note_id, seed, 0, 0.0))

        while queue:
            current_id, current, hops, inherited_bonus = queue.popleft()
            if hops >= self.max_hops:
                continue
            for relation in self._relations(current):
                target_id = self._target_id(relation)
                if not target_id or target_id not in candidates_by_id:
                    continue
                relation_type = str(relation.get("relation") or "related_to").casefold()
                weight = _RELATION_WEIGHTS.get(relation_type, 0.50)
                bonus = inherited_bonus + self.relation_bonus * weight / max(1, hops + 1)
                candidate = dict(candidates_by_id[target_id])
                previous = result.get(target_id)
                if previous is not None:
                    if bonus <= float(previous.get("graph_bonus", 0.0)):
                        continue
                candidate["graph_bonus"] = round(bonus, 6)
                candidate["graph_hops"] = hops + 1
                candidate["graph_relation"] = relation_type
                result[target_id] = candidate
                queue.append((target_id, candidate, hops + 1, bonus))

        return list(result.values())
