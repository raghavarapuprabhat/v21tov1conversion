"""Canonical field models (LLD v1.2 §2.2).

These are the normalized, source-agnostic representations the rest of the
system consumes. Every record keeps both the raw and normalized forms of key
values plus a `source` reference for audit. `Linkage` (per-context edge) lands
in E2 alongside the linkage resolver.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class MappingContext(str, Enum):
    """The three V2.1 mapping facets (one logically-grouped business object)."""
    ENTITY = "Entity"
    RP_IND = "RP_IND"
    RP_ORG = "RP_ORG"


class SourceRef(BaseModel):
    """Where a value came from, for audit (LLD §2.2)."""
    sheet: str
    row: int                       # 1-based Excel row
    column: Optional[str] = None   # column letter, when a single cell is referenced


class Occurs(BaseModel):
    """A Min/Max occurrence value that may be an int or 'unbounded'."""
    raw: Optional[str] = None
    value: Optional[int] = None
    unbounded: bool = False

    @property
    def is_array(self) -> bool:
        return self.unbounded or (self.value is not None and self.value > 1)


class V1Field(BaseModel):
    is_number_raw: Optional[str] = None
    is_number: Optional[str] = None        # normalized (upper, no spaces)
    dd_ref_raw: Optional[str] = None
    dd_ref: Optional[str] = None
    node_kind: Optional[str] = None        # Root / Element / ...
    path: list[str] = Field(default_factory=list)   # Level 1..8 (trailing blanks trimmed)
    attribute: Optional[str] = None
    xsd_type_raw: Optional[str] = None
    xsd_type: Optional[str] = None         # normalized token (casefold)
    nullable: Optional[bool] = None
    min_occurs: Optional[int] = None
    max_occurs: Occurs = Field(default_factory=Occurs)
    source: SourceRef


class V2Field(BaseModel):
    json_path: Optional[str] = None        # 'Schema Name + JSON Path'
    clmt_is_ref: Optional[str] = None
    version: Optional[str] = None
    change_log: Optional[str] = None
    clm_id: Optional[str] = None           # 'Attribute CLM ID'
    attribute_name: Optional[str] = None   # 'CCDM Attribute Name'
    dd_ref_raw: Optional[str] = None       # 'Source DD#'
    dd_ref: Optional[str] = None
    # The three context-mapping columns — raw + normalized (None when sentinel/blank)
    map_entity_raw: Optional[str] = None
    map_rp_ind_raw: Optional[str] = None
    map_rp_org_raw: Optional[str] = None
    map_entity: Optional[str] = None
    map_rp_ind: Optional[str] = None
    map_rp_org: Optional[str] = None
    repeat_remarks: Optional[str] = None
    node_kind: Optional[str] = None        # 'Node / Element'
    schema_name: Optional[str] = None
    json_attr: Optional[str] = None        # 'JSON Attribute Name'
    data_type_raw: Optional[str] = None
    data_type: Optional[str] = None        # normalized token (casefold)
    min_occurs: Optional[int] = None
    max_occurs: Occurs = Field(default_factory=Occurs)
    mandatory_optional: Optional[str] = None
    full_path: Optional[str] = None        # 'Schema + JSON Path + Attribute'
    mapping_remarks: Optional[str] = None
    source: SourceRef

    def mapped_is(self) -> dict[MappingContext, str]:
        """Distinct non-sentinel IS links by context (used by the E2 resolver)."""
        out: dict[MappingContext, str] = {}
        if self.map_entity:
            out[MappingContext.ENTITY] = self.map_entity
        if self.map_rp_ind:
            out[MappingContext.RP_IND] = self.map_rp_ind
        if self.map_rp_org:
            out[MappingContext.RP_ORG] = self.map_rp_org
        return out


class Linkage(BaseModel):
    """One context-tagged edge from a V2.1 row to a V1 IS (LLD §2.2, §4).

    `v1` is None when the mapped IS does not exist in V1 (a reverse-orphan,
    caught by gap engine G5).
    """
    is_number: str                 # normalized V1 IS this context points to
    context: MappingContext
    v2: V2Field
    v1: Optional[V1Field] = None

    @property
    def is_orphan(self) -> bool:
        return self.v1 is None
