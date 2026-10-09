"""NED (NASA/IPAC Extragalactic Database) client wrapping astroquery."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

log = logging.getLogger(__name__)


def _cell(value: Any) -> Any:
    if value is np.ma.masked:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class NedClient:
    def __init__(self, timeout: float = 20.0):
        self.timeout = timeout

    def query_object(self, name: str) -> dict[str, Any] | None:
        """Return the first NED row for ``name`` as a dict with NED's column names, or None."""
        from astroquery.ned import Ned  # imported lazily: astroquery is slow to import

        Ned.TIMEOUT = self.timeout
        table = Ned.query_object(name)
        if table is None or len(table) == 0:
            return None
        row = table[0]
        return {col: _cell(row[col]) for col in table.colnames}

    def query_region(
        self, ra_deg: float, dec_deg: float, radius_arcsec: float
    ) -> list[dict[str, Any]]:
        from astropy import units as u
        from astropy.coordinates import SkyCoord
        from astroquery.ned import Ned

        Ned.TIMEOUT = self.timeout
        coord = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame="icrs")
        table = Ned.query_region(coord, radius=radius_arcsec * u.arcsec)
        if table is None or len(table) == 0:
            return []
        rows = [{col: _cell(row[col]) for col in table.colnames} for row in table]
        rows.sort(key=lambda r: (r.get("Separation") is None, r.get("Separation") or 0.0))
        return rows
