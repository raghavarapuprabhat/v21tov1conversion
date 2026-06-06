"""Position-independent gap IDs (LLD v1.2 §5.7, Plan T-E3.7).

The id is built ONLY from stable business identity — never from a source cell
position (sheet/row/column) — so a re-uploaded Excel with reordered rows yields
the same id and comments/statuses re-attach (F13).
"""
from __future__ import annotations

from hashlib import sha1
from typing import Any, Optional


def make_gap_id(gap_type: Any, is_number: Optional[str], context: Any,
                v2_business_key: Optional[str], dimension: str) -> str:
    gt = getattr(gap_type, "value", gap_type)
    ctx = getattr(context, "value", context)
    parts = [str(gt), is_number or "", str(ctx or ""), v2_business_key or "", dimension]
    return sha1("|".join(parts).encode("utf-8")).hexdigest()[:16]


def v2_business_key(v2) -> str:
    """Stable V2-side identity for keying comparison gaps (LLD §5.7)."""
    return v2.full_path or v2.clm_id or v2.json_attr or ""
