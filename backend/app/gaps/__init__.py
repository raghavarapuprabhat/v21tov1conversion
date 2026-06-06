"""Gap analysis engines (E3). See LLD §5.

Planned modules:
    registry.py  - pluggable GapEngineRegistry
    typemap.py   - type-equivalence loader (config/type_equivalence.yaml)
    severity.py  - severity assignment (HLD §8)
    g1.py..g9.py - individual engines (G1..G4 mandatory; G5..G9 optional)
    gap_id.py    - position-independent business-key hashing (LLD §5.7)
"""
