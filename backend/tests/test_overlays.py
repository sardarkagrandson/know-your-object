from fastapi.testclient import TestClient

from app import main
from app.routers import surveys as surveys_router
from app.services.mocserver import MocRecord, MocServerClient

FITS = b"SIMPLE  =                    T / conforms to FITS standard" + b" " * 2000


class FakeMocServer(MocServerClient):
    def __init__(self, records=None, fits=FITS):
        super().__init__()
        self.records = records or {}
        self.fits = fits
        self.searches: list[str] = []

    def search(self, expression):
        self.searches.append(expression)
        return [MocRecord.from_json(r, expression) for r in self.records.get(expression, [])]

    def _get(self, params):  # pragma: no cover - the fake never hits the network
        raise AssertionError("network call attempted")

    def fetch_moc_fits(self, record_id):
        if self.fits is None:
            raise ValueError("no moc")
        return self.fits


def _client(monkeypatch, fake):
    monkeypatch.setattr(surveys_router, "get_mocserver", lambda: fake)
    return TestClient(main.app)


def test_resolve_prefers_widest_coverage_and_falls_through_expressions(monkeypatch):
    fake = FakeMocServer(
        records={
            "ID=CDS/B/hst/*": [],
            "ID=*hst*&&dataproduct_type=catalog": [
                {"ID": "CDS/B/hst/small", "obs_title": "small", "moc_sky_fraction": 0.001},
                {"ID": "CDS/B/hst/log", "obs_title": "HST log", "moc_sky_fraction": 0.02},
                {"ID": "CDS/B/hst/empty", "obs_title": "empty", "moc_sky_fraction": 0},
            ],
        }
    )
    client = _client(monkeypatch, fake)
    body = client.get("/api/overlays/hst").json()
    assert body["resolved"] is True
    assert body["record_id"] == "CDS/B/hst/log"
    assert body["expression"] == "ID=*hst*&&dataproduct_type=catalog"
    assert body["moc_url"] == "/api/overlays/hst/moc"
    # Resolution is cached: a second call performs no new searches.
    n = len(fake.searches)
    client.get("/api/overlays/hst")
    assert len(fake.searches) == n


def test_moc_endpoint_serves_fits(monkeypatch):
    fake = FakeMocServer(
        records={"ID=CDS/B/hst/*": [{"ID": "CDS/B/hst/log", "moc_sky_fraction": 0.02}]}
    )
    client = _client(monkeypatch, fake)
    res = client.get("/api/overlays/hst/moc")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/fits")
    assert res.headers["x-moc-record"] == "CDS/B/hst/log"
    assert res.content.startswith(b"SIMPLE  =")


def test_moc_endpoint_reports_unresolved_overlay(monkeypatch):
    client = _client(monkeypatch, FakeMocServer())
    res = client.get("/api/overlays/jwst/moc")
    assert res.status_code == 502
    assert "No MOCServer record" in res.json()["detail"]
    assert client.get("/api/overlays/nope/moc").status_code == 404


def test_surveys_catalog_points_overlays_at_proxy(monkeypatch):
    client = _client(monkeypatch, FakeMocServer())
    body = client.get("/api/surveys").json()
    assert all(o["moc_url"].startswith("/api/overlays/") for o in body["overlays"])
