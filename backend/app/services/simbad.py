"""Thin SIMBAD TAP client built on pyvo.

We issue explicit ADQL instead of using ``astroquery.simbad`` so that the set of returned
columns is fixed and known (astroquery >= 0.4.8 fetches column metadata lazily over the
network, which makes behaviour harder to pin down and to test).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import requests
from pyvo.dal import TAPService

log = logging.getLogger(__name__)

BASIC_COLUMNS = (
    "oid, main_id, ra, dec, otype, morph_type, morph_qual, "
    "rvz_radvel, rvz_redshift, rvz_err, rvz_type, rvz_qual, "
    "galdim_majaxis, galdim_minaxis, galdim_angle, plx_value"
)

# SIMBAD object types that denote galaxy groups / clusters / pairs.
GROUP_OTYPES = ("ClG", "GrG", "CGG", "PaG", "IG", "SCG")

# Fallback labels for common SIMBAD object types (used if the otypedef lookup fails).
OTYPE_LABELS = {
    "G": "Galaxy",
    "GiG": "Galaxy in Group of Galaxies",
    "GiC": "Galaxy in Cluster of Galaxies",
    "GiP": "Galaxy in Pair of Galaxies",
    "AGN": "Active Galaxy Nucleus",
    "SyG": "Seyfert Galaxy",
    "Sy1": "Seyfert 1 Galaxy",
    "Sy2": "Seyfert 2 Galaxy",
    "LIN": "LINER-type Active Galaxy Nucleus",
    "QSO": "Quasar",
    "BLL": "BL Lac",
    "Bla": "Blazar",
    "rG": "Radio Galaxy",
    "SBG": "Starburst Galaxy",
    "EmG": "Emission-line galaxy",
    "IG": "Interacting Galaxies",
    "PaG": "Pair of Galaxies",
    "GrG": "Group of Galaxies",
    "CGG": "Compact Group of Galaxies",
    "ClG": "Cluster of Galaxies",
    "SCG": "Supercluster of Galaxies",
    "H2G": "HII Galaxy",
    "LSB": "Low Surface Brightness Galaxy",
    "BiC": "Brightest Galaxy in a Cluster (BCG)",
    "HII": "HII Region",
    "PN": "Planetary Nebula",
    "SNR": "SuperNova Remnant",
    "SN*": "SuperNova",
    "GlC": "Globular Cluster",
    "OpC": "Open Cluster",
    "*": "Star",
    "Cl*": "Cluster of Stars",
    "MoC": "Molecular Cloud",
    "Neb": "Nebula",
}


class _TimeoutSession(requests.Session):
    """requests.Session that applies a default timeout to every request."""

    def __init__(self, timeout: float):
        super().__init__()
        self._timeout = timeout

    def request(self, method, url, **kwargs):  # type: ignore[override]
        kwargs.setdefault("timeout", self._timeout)
        return super().request(method, url, **kwargs)


def _escape(value: str) -> str:
    return value.replace("'", "''")


def _cell(value: Any) -> Any:
    """Convert an astropy table cell into a plain Python value (masked -> None)."""
    if value is np.ma.masked:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, np.generic):
        value = value.item()
    if isinstance(value, float) and np.isnan(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


class SimbadClient:
    def __init__(self, tap_url: str, timeout: float = 20.0):
        self.tap_url = tap_url
        self.timeout = timeout
        self._service: TAPService | None = None

    @property
    def service(self) -> TAPService:
        if self._service is None:
            self._service = TAPService(self.tap_url, session=_TimeoutSession(self.timeout))
        return self._service

    # -- low level ---------------------------------------------------------------------------
    def run(self, adql: str, maxrec: int = 200) -> list[dict[str, Any]]:
        """Execute an ADQL query and return rows as dicts of plain Python values."""
        log.debug("SIMBAD ADQL: %s", adql)
        table = self.service.run_sync(adql, maxrec=maxrec).to_table()
        rows: list[dict[str, Any]] = []
        for row in table:
            rows.append({name: _cell(row[name]) for name in table.colnames})
        return rows

    # -- queries -----------------------------------------------------------------------------
    def basic_by_name(self, name: str) -> dict[str, Any] | None:
        """Look up an object by any of its identifiers (SIMBAD normalises the name)."""
        adql = (
            f"SELECT TOP 1 {BASIC_COLUMNS}, ident.id AS matched_id "
            "FROM basic JOIN ident ON ident.oidref = basic.oid "
            f"WHERE ident.id = '{_escape(name)}'"
        )
        rows = self.run(adql, maxrec=1)
        return rows[0] if rows else None

    def basic_near(self, ra_deg: float, dec_deg: float, radius_deg: float, limit: int = 10):
        """Objects within ``radius_deg`` of a position, nearest first."""
        adql = (
            f"SELECT TOP {int(limit)} {BASIC_COLUMNS}, "
            f"DISTANCE(POINT('ICRS', basic.ra, basic.dec), POINT('ICRS', {ra_deg}, {dec_deg})) "
            "AS sep_deg "
            "FROM basic "
            f"WHERE CONTAINS(POINT('ICRS', basic.ra, basic.dec), "
            f"CIRCLE('ICRS', {ra_deg}, {dec_deg}, {radius_deg})) = 1 "
            "ORDER BY sep_deg ASC"
        )
        return self.run(adql, maxrec=limit)

    def identifiers(self, oid: int) -> list[str]:
        rows = self.run(f"SELECT id FROM ident WHERE oidref = {int(oid)}", maxrec=500)
        return [r["id"] for r in rows if r.get("id")]

    def distances(self, oid: int) -> list[dict[str, Any]]:
        adql = (
            "SELECT dist, unit, minus_err, plus_err, method, qual, bibcode "
            f"FROM mesDistance WHERE oidref = {int(oid)} ORDER BY bibcode DESC"
        )
        return self.run(adql, maxrec=50)

    def otype_label(self, otype: str) -> str | None:
        try:
            rows = self.run(
                f"SELECT label, description FROM otypedef WHERE otype = '{_escape(otype)}'",
                maxrec=1,
            )
        except Exception as exc:  # noqa: BLE001 - best effort, fall back to static map
            log.debug("otypedef lookup failed for %s: %s", otype, exc)
            rows = []
        if rows:
            return rows[0].get("description") or rows[0].get("label")
        return OTYPE_LABELS.get(otype)

    def groups_near(self, ra_deg: float, dec_deg: float, radius_deg: float, limit: int = 10):
        """Galaxy groups/clusters/pairs within ``radius_deg`` of a position, nearest first."""
        otypes = ", ".join(f"'{t}'" for t in GROUP_OTYPES)
        adql = (
            f"SELECT TOP {int(limit)} main_id, otype, rvz_redshift, "
            f"DISTANCE(POINT('ICRS', basic.ra, basic.dec), POINT('ICRS', {ra_deg}, {dec_deg})) "
            "AS sep_deg "
            "FROM basic "
            f"WHERE otype IN ({otypes}) AND "
            f"CONTAINS(POINT('ICRS', basic.ra, basic.dec), "
            f"CIRCLE('ICRS', {ra_deg}, {dec_deg}, {radius_deg})) = 1 "
            "ORDER BY sep_deg ASC"
        )
        return self.run(adql, maxrec=limit)
