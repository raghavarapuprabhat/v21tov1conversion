"""Type-equivalence map loader (LLD v1.2 §5.4, used by G3).

Loads config/type_equivalence.yaml into reverse lookups: a normalized source
token -> canonical type. Tokens absent from the map return None, which G3 treats
as 'indeterminate' (flagged, never silently matched).
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml


class TypeMap:
    def __init__(self, v1_tokens: dict[str, str], v2_tokens: dict[str, str]):
        self._v1 = v1_tokens
        self._v2 = v2_tokens

    @classmethod
    def load(cls, path: str | Path) -> "TypeMap":
        data = yaml.safe_load(Path(path).read_text()) or {}
        v1: dict[str, str] = {}
        v2: dict[str, str] = {}
        for canonical, sides in data.items():
            for tok in (sides or {}).get("v1", []) or []:
                v1[str(tok).strip().casefold()] = canonical
            for tok in (sides or {}).get("v2", []) or []:
                v2[str(tok).strip().casefold()] = canonical
        return cls(v1, v2)

    def canon_v1(self, token: Optional[str]) -> Optional[str]:
        return self._v1.get(token) if token else None

    def canon_v2(self, token: Optional[str]) -> Optional[str]:
        return self._v2.get(token) if token else None
