from fastapi.testclient import TestClient

from app import main
from app.services import resolver as resolver_module
from tests.conftest import FakeNed, FakeSimbad


def _client(monkeypatch, settings, simbad_kw=None, ned_kw=None):
    r = resolver_module.TargetResolver(
        settings=settings, simbad=FakeSimbad(**(simbad_kw or {})), ned=FakeNed(**(ned_kw or {}))
    )
    monkeypatch.setattr(main.resolver, "get_resolver", lambda: r)
    return TestClient(main.app)


def test_health(monkeypatch, settings):
    client = _client(monkeypatch, settings)
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["modules"]["resolver"] is True


def test_resolve_endpoint(monkeypatch, settings):
    client = _client(monkeypatch, settings)
    res = client.get("/api/resolve", params={"q": "NGC 1365"})
    assert res.status_code == 200
    body = res.json()
    assert body["main_id"] == "NGC  1365"
    assert body["coordinates"]["ra_deg"] > 53
    assert body["kinematics"]["redshift"] > 0


def test_resolve_bad_coordinates_is_400(monkeypatch, settings):
    client = _client(monkeypatch, settings)
    res = client.get("/api/resolve", params={"q": "400.0, 10.0"})
    assert res.status_code == 400


def test_resolve_not_found_is_404(monkeypatch, settings):
    from astropy.coordinates import SkyCoord

    monkeypatch.setattr(
        SkyCoord, "from_name", staticmethod(lambda n: (_ for _ in ()).throw(ValueError("nope")))
    )
    client = _client(monkeypatch, settings, simbad_kw={"basic": None}, ned_kw={"row": None})
    res = client.get("/api/resolve", params={"q": "Nothing Here"})
    assert res.status_code == 404


def test_surveys_endpoint(monkeypatch, settings):
    client = _client(monkeypatch, settings)
    body = client.get("/api/surveys").json()
    assert len(body["default_grid"]) == 4
    ids = {s["id"] for s in body["surveys"]}
    assert set(body["default_grid"]) <= ids
    assert body["overlays"]
