"""Coordinate parsing and formatting helpers.

The resolver accepts either an object name or a coordinate pair. We only treat the input as
coordinates when it cannot plausibly be a catalog name: letters other than the sexagesimal
markers (h, m, s, d) make it a name ("NGC 1365", "3C 273", "PKS 2155-304").
"""

from __future__ import annotations

import re

import astropy.units as u
from astropy.coordinates import SkyCoord

_NON_COORD_LETTERS = re.compile(r"[a-ce-gi-ln-rt-zA-CE-GI-LN-RT-Z]")
_FLOAT = r"[+-]?\d+(?:\.\d+)?"
_TWO_FLOATS = re.compile(rf"^\s*({_FLOAT})\s*[,\s]\s*({_FLOAT})\s*$")
_COMPACT_J = re.compile(
    r"^\s*J?(\d{2})(\d{2})(\d{2}(?:\.\d+)?)\s*([+-])(\d{2})(\d{2})(\d{2}(?:\.\d+)?)\s*$"
)
_SEX_TOKENS = re.compile(r"^[\s\d\.\+\-:hmsd]+$")


def parse_coordinates(text: str) -> SkyCoord | None:
    """Return an ICRS ``SkyCoord`` if ``text`` looks like a coordinate pair, else ``None``."""
    s = text.strip()
    if not s:
        return None

    # Compact IAU-style designation: J033336.4-360825
    m = _COMPACT_J.match(s)
    if m:
        hh, mm, ss, sign, dd, dm, ds = m.groups()
        return SkyCoord(f"{hh}h{mm}m{ss}s", f"{sign}{dd}d{dm}m{ds}s", frame="icrs")

    if _NON_COORD_LETTERS.search(s):
        return None  # contains letters that are not sexagesimal markers -> a name

    # Two decimal numbers: degrees, degrees
    m = _TWO_FLOATS.match(s)
    if m:
        ra, dec = float(m.group(1)), float(m.group(2))
        if not (0.0 <= ra < 360.0 and -90.0 <= dec <= 90.0):
            raise ValueError(f"Coordinates out of range: RA={ra}, Dec={dec}")
        return SkyCoord(ra=ra * u.deg, dec=dec * u.deg, frame="icrs")

    if not _SEX_TOKENS.match(s):
        return None

    # Sexagesimal with h/m/s or ':' separators -> hours for RA, degrees for Dec
    normalised = s.replace(",", " ")
    tokens = normalised.split()
    try:
        if "h" in normalised or ":" in normalised:
            if len(tokens) == 2:
                return SkyCoord(tokens[0], tokens[1], frame="icrs", unit=(u.hourangle, u.deg))
            return SkyCoord(normalised, frame="icrs", unit=(u.hourangle, u.deg))
        if len(tokens) == 6:
            ra = " ".join(tokens[:3])
            dec = " ".join(tokens[3:])
            return SkyCoord(ra, dec, frame="icrs", unit=(u.hourangle, u.deg))
    except (ValueError, u.UnitsError) as exc:
        raise ValueError(f"Could not parse coordinates from '{text}': {exc}") from exc
    return None


def format_coordinates(coord: SkyCoord) -> tuple[str, str]:
    """Return (RA as hh:mm:ss.ss, Dec as +dd:mm:ss.s)."""
    icrs = coord.icrs
    ra = icrs.ra.to_string(unit=u.hourangle, sep=":", precision=2, pad=True)
    dec = icrs.dec.to_string(unit=u.deg, sep=":", precision=1, alwayssign=True, pad=True)
    return ra, dec
