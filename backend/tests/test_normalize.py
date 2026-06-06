"""Unit tests for normalization (LLD §3.2), covering the DQ cases seen in
the sample data: 'Not APplicable', 'XS:integer', boolean Nullable, occurrence."""
from app.ingestion import normalize as N


def test_clean_collapses_whitespace():
    assert N.clean("  a   b ") == "a b"
    assert N.clean("") is None
    assert N.clean(None) is None


def test_sentinels_any_casing():
    assert N.is_sentinel("Not Applicable")
    assert N.is_sentinel("Not APplicable")   # observed odd casing
    assert N.is_sentinel("n/a")
    assert N.is_sentinel("")
    assert not N.is_sentinel("IS2339")


def test_norm_code_uppercases_and_drops_sentinels():
    assert N.norm_code("is2339") == "IS2339"
    assert N.norm_code(" IS 1 ") == "IS1"
    assert N.norm_code("Not APplicable") is None


def test_norm_type_token():
    assert N.norm_type_token("XS:integer") == "xs:integer"
    assert N.norm_type_token("String") == "string"
    assert N.norm_type_token(None) is None


def test_norm_bool():
    assert N.norm_bool(True) is True
    assert N.norm_bool(False) is False
    assert N.norm_bool("true") is True
    assert N.norm_bool("0") is False
    assert N.norm_bool("maybe") is None


def test_parse_occurs():
    assert N.parse_occurs(1).value == 1
    assert N.parse_occurs("1").value == 1
    u = N.parse_occurs("unbounded")
    assert u.unbounded and u.is_array
    assert N.parse_occurs(None).value is None
    assert N.parse_occurs("3").is_array is True
