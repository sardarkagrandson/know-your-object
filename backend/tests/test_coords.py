import pytest

from app.services.coords import format_coordinates, parse_coordinates


@pytest.mark.parametrize(
    "text",
    ["NGC 1365", "M 31", "3C 273", "PKS 2155-304", "Fornax A", "SDSS J1234+5678", "ngc1365"],
)
def test_names_are_not_coordinates(text):
    assert parse_coordinates(text) is None


@pytest.mark.parametrize(
    "text, ra, dec",
    [
        ("53.4015, -36.1404", 53.4015, -36.1404),
        ("53.4015 -36.1404", 53.4015, -36.1404),
        ("03h33m36.4s -36d08m25s", 53.40167, -36.14028),
        ("03:33:36.4 -36:08:25", 53.40167, -36.14028),
        ("03 33 36.4 -36 08 25", 53.40167, -36.14028),
        ("J033336.4-360825", 53.40167, -36.14028),
        ("033336.4-360825", 53.40167, -36.14028),
        ("12 30 49.4 +12 23 28", 187.70583, 12.39111),
    ],
)
def test_coordinate_formats(text, ra, dec):
    c = parse_coordinates(text)
    assert c is not None
    assert c.ra.deg == pytest.approx(ra, abs=2e-4)
    assert c.dec.deg == pytest.approx(dec, abs=2e-4)


def test_out_of_range_degrees_raises():
    with pytest.raises(ValueError):
        parse_coordinates("400.0, 10.0")


def test_format_roundtrip():
    c = parse_coordinates("03h33m36.4s -36d08m25s")
    ra, dec = format_coordinates(c)
    assert ra == "03:33:36.40"
    assert dec == "-36:08:25.0"
