"""V2.1 -> V1 Schema Conversion — Gap Analysis Dashboard (backend).

Package layout (see LLD v1.2 §15):
    app.config        - settings (.env)
    app.api           - FastAPI routers
    app.models        - pydantic canonical + gap/comment/status models   (E2/E3)
    app.ingestion     - excel loader, normalizer, validator              (E1)
    app.domain        - per-context linkage, tree builder                (E2/E4)
    app.gaps          - gap engine registry G1..G9, type map, severity   (E3)
    app.repositories  - storage abstraction (in-memory+snapshot/postgres)(E5)
    app.services      - comments, status+history, v2 lookup, saved views (E6/E7)
"""

__version__ = "0.1.0"
