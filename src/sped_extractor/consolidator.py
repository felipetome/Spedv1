from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Sequence, Tuple

from .config import consolidation, defaults
from .utils import ensure_defaults


def _key_from_item(item: dict, keys: Sequence[str]) -> Tuple:
    return tuple(item.get(key) for key in keys)


@dataclass
class Consolidator:
    join_keys: Sequence[str] = consolidation.join_keys
    items: Dict[Tuple, dict] = field(default_factory=dict)

    def ingest(self, records: Iterable[dict]) -> None:
        for record in records:
            record = ensure_defaults(dict(record))
            key = _key_from_item(record, self.join_keys)
            if key not in self.items:
                self.items[key] = record
                continue
            self._merge(self.items[key], record)

    @staticmethod
    def _merge(target: dict, source: dict) -> None:
        for field, value in source.items():
            if value is None:
                continue
            if field in {"Pis_Mono", "Cofins_Mono"}:
                target[field] = bool(target.get(field)) or bool(value)
                continue
            if field in defaults.numeric_zero_if_missing or isinstance(value, (int, float)):
                if target.get(field) in (None, 0, 0.0):
                    target[field] = value
                elif field == "VALUE" and value:
                    # Merge by keeping the maximum per item
                    target[field] = max(target[field], value)
                continue
            if not target.get(field):
                target[field] = value

    def to_list(self) -> List[dict]:
        return list(self.items.values())

