"""Deterministic, non-destructive normalization (LLD v1.2 §3.2).

Rules are table-driven and case/whitespace-tolerant for *matching* only — the
raw value is always preserved by callers for display and audit. Grounded in the
data-quality realities observed in the sample workbooks (e.g. 'Not APplicable',
'XS:integer', boolean Nullable).
"""
from __future__ import annotations

import re
from typing import Any, Optional

from app.models.canonical import Occurs

# Tokens that mean "no mapping / not applicable" in the CC_V1_Mapping columns.
SENTINELS = {"", "not applicable", "n/a", "na", "none", "null", "tbd", "tbc", "-"}

_TRUE = {"true", "1", "yes", "y", "t"}
_FALSE = {"false", "0", "no", "n", "f"}
_UNBOUNDED = {"unbounded", "*", "n", "many", "-1"}


def clean(value: Any) -> Optional[str]:
    """Trim and collapse internal whitespace runs; return None for empty."""
    if value is None:
        return None
    s = re.sub(r"\s+", " ", str(value).strip())
    return s or None


def is_sentinel(value: Any) -> bool:
    """True for blank / 'Not Applicable' style no-mapping tokens (any casing)."""
    s = clean(value)
    return s is None or s.casefold() in SENTINELS


def norm_key(value: Any) -> Optional[str]:
    """Case-folded comparison key; None for sentinels/empty."""
    s = clean(value)
    if s is None or s.casefold() in SENTINELS:
        return None
    return s.casefold()


def norm_code(value: Any) -> Optional[str]:
    """Normalize an IS / DD code (upper, no internal spaces); None for sentinel."""
    if is_sentinel(value):
        return None
    return clean(value).upper().replace(" ", "")  # type: ignore[union-attr]


def norm_type_token(value: Any) -> Optional[str]:
    """Lowercase type token for the equivalence map (e.g. 'XS:integer'->'xs:integer')."""
    s = clean(value)
    return s.casefold() if s else None


def norm_bool(value: Any) -> Optional[bool]:
    """Parse a Nullable value to bool; None when indeterminate."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    s = clean(value)
    if s is None:
        return None
    low = s.casefold()
    if low in _TRUE:
        return True
    if low in _FALSE:
        return False
    return None


def parse_int(value: Any) -> Optional[int]:
    """Parse an integer occurrence (Min); None when blank/unparseable."""
    s = clean(value)
    if s is None:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def parse_occurs(value: Any) -> Occurs:
    """Parse a Max occurrence which may be int or 'unbounded'/'*'/'n'."""
    s = clean(value)
    if s is None:
        return Occurs(raw=None)
    if s.casefold() in _UNBOUNDED:
        return Occurs(raw=s, unbounded=True)
    try:
        return Occurs(raw=s, value=int(float(s)))
    except ValueError:
        return Occurs(raw=s)  # keep raw; flagged as DQ by the validator
