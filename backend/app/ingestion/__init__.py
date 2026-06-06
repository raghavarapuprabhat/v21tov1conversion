"""Excel ingestion & normalization (E1). See LLD §3.

Planned modules:
    excel_loader.py - openpyxl reader + header-row detection
    normalize.py    - trim/casefold, sentinel detection, IS/bool/occurrence parse
    validate.py     - row validation + data-quality findings (feeds G9)
"""
