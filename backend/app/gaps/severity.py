"""Severity assignment (HLD §8, Plan T-E3.6). Thresholds are intentionally
simple and centralized here so they are easy to tune later."""
from __future__ import annotations

from app.models.gap import Severity


def coverage_severity(nullable_false: bool, parent_min_1: bool) -> Severity:
    if parent_min_1:
        return Severity.CRITICAL        # required V1 field with no V2 source
    if nullable_false:
        return Severity.HIGH
    return Severity.MEDIUM


def datatype_severity(mandatory: bool) -> Severity:
    return Severity.HIGH if mandatory else Severity.MEDIUM


def occurrence_severity(is_array: bool) -> Severity:
    return Severity.HIGH if is_array else Severity.MEDIUM
