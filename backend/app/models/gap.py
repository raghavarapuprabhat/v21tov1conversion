"""Gap / status / severity models (LLD v1.2 §2.3)."""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.canonical import MappingContext, SourceRef


class GapType(str, Enum):
    G1_COVERAGE = "G1_COVERAGE"
    G2_OCCURRENCE = "G2_OCCURRENCE"
    G3_DATATYPE = "G3_DATATYPE"
    G4_MANDATORY = "G4_MANDATORY"
    G5_REVERSE_ORPHAN = "G5_REVERSE_ORPHAN"   # optional
    G6_DD_MISMATCH = "G6_DD_MISMATCH"         # optional
    G7_CARDINALITY = "G7_CARDINALITY"         # optional
    G8_DUP_MAPPING = "G8_DUP_MAPPING"         # optional
    G9_DATA_QUALITY = "G9_DATA_QUALITY"       # optional


class GapStatus(str, Enum):
    OPEN = "Open"
    ACCEPTED = "Accepted"
    NOT_APPLICABLE = "Not applicable"


class Severity(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Gap(BaseModel):
    gap_id: str
    gap_type: GapType
    is_number: Optional[str] = None
    mapping_context: Optional[MappingContext] = None
    v1_path: Optional[str] = None        # Level 1..8 joined (display + multi-select filter)
    v1_ref: Optional[SourceRef] = None
    v2_ref: Optional[SourceRef] = None
    v1_value: Optional[str] = None
    v2_value: Optional[str] = None
    detail: str = ""
    flags: dict[str, Any] = Field(default_factory=dict)
    severity: Severity = Severity.MEDIUM
    root_node: Optional[str] = None
    dd_ref: Optional[str] = None
    nullable: Optional[bool] = None      # V1 Nullable (surfaced on G1 coverage gaps)
    dd_in_v2: bool = False               # is this DD number present in the V2.1 sheet?
    status: GapStatus = GapStatus.OPEN
