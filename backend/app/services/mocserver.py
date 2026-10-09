"""Client for the CDS MOCServer (https://alasky.cds.unistra.fr/MocServer/query).

The MOCServer knows the sky coverage (MOC) of every HiPS, VizieR table and many mission
observation logs. We use it to find the coverage record for a mission/instrument and to fetch
that coverage as a FITS MOC, which is the format Aladin Lite's ``A.MOCFromURL`` expects.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx

log = logging.getLogger(__name__)

MOCSERVER_URL = "https://alasky.cds.unistra.fr/MocServer/query"
FITS_MAGIC = b"SIMPLE  ="


@dataclass
class MocRecord:
    id: str
    title: str | None
    sky_fraction: float | None
    dataproduct_type: str | None
    expression: str

    @classmethod
    def from_json(cls, rec: dict[str, Any], expression: str) -> MocRecord:
        frac = rec.get("moc_sky_fraction")
        try:
            frac_f = float(frac) if frac is not None else None
        except (TypeError, ValueError):
            frac_f = None
        return cls(
            id=str(rec.get("ID", "")),
            title=rec.get("obs_title") or rec.get("obs_collection"),
            sky_fraction=frac_f,
            dataproduct_type=rec.get("dataproduct_type"),
            expression=expression,
        )


class MocServerClient:
    def __init__(
        self, base_url: str = MOCSERVER_URL, timeout: float = 30.0, cache_ttl: int = 86400
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.cache_ttl = cache_ttl
        self._record_cache: dict[str, tuple[float, MocRecord | None]] = {}
        self._moc_cache: dict[str, tuple[float, bytes]] = {}
        self._lock = threading.Lock()

    # -- HTTP ----------------------------------------------------------------------------------
    def _get(self, params: dict[str, str]) -> httpx.Response:
        with httpx.Client(timeout=self.timeout, follow_redirects=True) as client:
            res = client.get(self.base_url, params=params, headers={"User-Agent": "AstroScope/0.1"})
            res.raise_for_status()
            return res

    def search(self, expression: str) -> list[MocRecord]:
        """Records matching a MOCServer expression, e.g. ``ID=CDS/B/hst/*``."""
        res = self._get(
            {
                "expr": expression,
                "get": "record",
                "fmt": "json",
                "fields": "ID,obs_title,obs_collection,moc_sky_fraction,dataproduct_type",
            }
        )
        data = res.json()
        if not isinstance(data, list):
            raise ValueError(f"Unexpected MOCServer response for {expression!r}")
        return [MocRecord.from_json(r, expression) for r in data if isinstance(r, dict)]

    def fetch_moc_fits(self, record_id: str) -> bytes:
        """The coverage of one record as a FITS MOC (bytes)."""
        now = time.monotonic()
        with self._lock:
            hit = self._moc_cache.get(record_id)
            if hit and hit[0] > now:
                return hit[1]
        data: bytes | None = None
        for params in (
            {"ID": record_id, "get": "moc"},
            {"ID": record_id, "get": "moc", "fmt": "fits"},
        ):
            res = self._get(params)
            if res.content.startswith(FITS_MAGIC):
                data = res.content
                break
        if data is None:
            raise ValueError(f"MOCServer did not return a FITS MOC for {record_id!r}")
        with self._lock:
            self._moc_cache[record_id] = (now + self.cache_ttl, data)
        return data

    # -- resolution ----------------------------------------------------------------------------
    def resolve(self, key: str, expressions: list[str]) -> MocRecord | None:
        """Try each expression in turn; return the matching record with the widest coverage."""
        now = time.monotonic()
        with self._lock:
            hit = self._record_cache.get(key)
            if hit and hit[0] > now and hit[1] is not None:
                return hit[1]
        chosen: MocRecord | None = None
        for expr in expressions:
            try:
                records = self.search(expr)
            except Exception as exc:  # noqa: BLE001 - remote service
                log.warning("MOCServer search failed for %r: %s", expr, exc)
                continue
            usable = [r for r in records if r.id and (r.sky_fraction or 0) > 0]
            if not usable:
                continue
            usable.sort(key=lambda r: r.sky_fraction or 0, reverse=True)
            chosen = usable[0]
            log.info(
                "Overlay %s resolved to %s (%s, sky fraction %.4g) via %r",
                key,
                chosen.id,
                chosen.title,
                chosen.sky_fraction or 0,
                expr,
            )
            break
        with self._lock:
            self._record_cache[key] = (now + self.cache_ttl, chosen)
        return chosen


_client: MocServerClient | None = None
_client_lock = threading.Lock()


def get_mocserver() -> MocServerClient:
    global _client
    with _client_lock:
        if _client is None:
            from app.config import get_settings

            settings = get_settings()
            _client = MocServerClient(
                base_url=settings.mocserver_url, timeout=settings.remote_timeout * 1.5
            )
        return _client
