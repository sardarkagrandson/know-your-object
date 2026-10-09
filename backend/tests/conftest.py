"""Shared fixtures: a resolver wired to fake SIMBAD / NED clients (no network)."""

from __future__ import annotations

import pytest

from app.config import Settings
from app.services.resolver import TargetResolver

NGC1365_BASIC = {
    "oid": 1136524,
    "main_id": "NGC  1365",
    "ra": 53.40152,
    "dec": -36.14040,
    "otype": "Sy1",
    "morph_type": "SB(s)b",
    "morph_qual": "C",
    "rvz_radvel": 1636.0,
    "rvz_redshift": 0.005457,
    "rvz_err": 1.0,
    "rvz_type": "v",
    "rvz_qual": "A",
    "galdim_majaxis": 11.22,
    "galdim_minaxis": 6.17,
    "galdim_angle": 32.0,
    "plx_value": None,
    "matched_id": "NGC  1365",
}

NGC1365_IDS = ["NGC  1365", "FCC 121", "ESO 358-17", "2MASX J03333647-3608263", "LGG  94"]

NGC1365_DISTANCES = [
    {
        "dist": 18.1,
        "unit": "Mpc",
        "minus_err": 1.0,
        "plus_err": 1.0,
        "method": "TRGB",
        "qual": None,
        "bibcode": "2013AJ....146...86T",
    },
]

NGC1365_GROUPS = [
    {"main_id": "NAME Fornax Cluster", "otype": "ClG", "rvz_redshift": 0.00475, "sep_deg": 0.9},
    {"main_id": "NGC  1365", "otype": "GrG", "rvz_redshift": 0.0054, "sep_deg": 0.0},
]

NGC1365_NED = {
    "Object Name": "NGC 1365",
    "RA": 53.40155,
    "DEC": -36.14043,
    "Type": "G",
    "Velocity": 1636,
    "Redshift": 0.005457,
    "Redshift Flag": "SLS",
}


class FakeSimbad:
    def __init__(self, basic=NGC1365_BASIC, fail=False):
        self.basic = basic
        self.fail = fail
        self.calls: list[tuple] = []

    def _check(self):
        if self.fail:
            raise ConnectionError("simulated SIMBAD outage")

    def basic_by_name(self, name):
        self.calls.append(("basic_by_name", name))
        self._check()
        return dict(self.basic) if self.basic else None

    def basic_near(self, ra, dec, radius_deg, limit=10):
        self.calls.append(("basic_near", ra, dec, radius_deg))
        self._check()
        if self.basic is None:
            return []
        return [dict(self.basic, sep_deg=0.0002)]

    def identifiers(self, oid):
        self.calls.append(("identifiers", oid))
        self._check()
        return list(NGC1365_IDS)

    def distances(self, oid):
        self.calls.append(("distances", oid))
        self._check()
        return [dict(d) for d in NGC1365_DISTANCES]

    def otype_label(self, otype):
        self.calls.append(("otype_label", otype))
        self._check()
        return "Seyfert 1 Galaxy"

    def groups_near(self, ra, dec, radius_deg, limit=10):
        self.calls.append(("groups_near", ra, dec, radius_deg))
        self._check()
        return [dict(g) for g in NGC1365_GROUPS]


class FakeNed:
    def __init__(self, row=NGC1365_NED, fail=False):
        self.row = row
        self.fail = fail
        self.calls: list[tuple] = []

    def query_object(self, name):
        self.calls.append(("query_object", name))
        if self.fail:
            raise TimeoutError("simulated NED timeout")
        return dict(self.row) if self.row else None


@pytest.fixture
def settings():
    return Settings(_env_file=None, ASTROSCOPE_CACHE_TTL=60)


@pytest.fixture
def resolver(settings):
    return TargetResolver(settings=settings, simbad=FakeSimbad(), ned=FakeNed())
