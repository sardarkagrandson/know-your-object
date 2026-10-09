# AstroScope

Astronomical target reconnaissance and multi-wavelength analysis. Type an object name or a
coordinate pair, get its basic properties from SIMBAD / NED, and inspect it in four synchronised
Aladin Lite v3 sky views across different surveys.

## Status

| Module | Description | State |
| --- | --- | --- |
| 1 | Target resolver & basic metadata (SIMBAD TAP, NED, Sesame) | implemented |
| 2 | Synced 2x2 Aladin Lite viewer with per-pane surveys and MOC overlays | implemented |
| 3 | Archive cross-matching via ObsCore TAP (ESO, MAST, ALMA) + HI surveys | planned |
| 4 | ESO DataLink/SODA MUSE cutouts, 1D spectra, HI overplot | planned |
| 5 | ADS literature & bibliometrics | planned |
| 6 | LLM scientific synthesis | planned |

## Layout

```
backend/            FastAPI application (Python 3.11+)
  app/main.py       app factory, CORS, routers
  app/config.py     settings (loaded from the repo-root .env)
  app/schemas/      Pydantic response models
  app/services/     coords parsing, SIMBAD TAP client, NED client, resolver, survey catalog
  app/routers/      /api/resolve, /api/surveys, /api/health
  tests/            pytest suite (remote services are faked; no network needed)
frontend/           React 18 + TypeScript + Tailwind, Vite
  src/lib/viewSync.ts      pan/zoom/FOV synchronisation between Aladin instances
  src/components/          TargetSearch, TargetCard, AladinGrid, AladinPane
```

## Quick start

```bash
cp .env.example .env            # fill in ADS_DEV_KEY / LLM keys later (not needed for modules 1-2)
make setup                      # python venv + npm install
make backend                    # http://localhost:8000  (OpenAPI docs at /docs)
make frontend                   # http://localhost:5173  (proxies /api to the backend)
```

Then open http://localhost:5173 and resolve e.g. `NGC 1365`, `M 87`, `03h33m36.4s -36d08m25s`
or `187.706, 12.391`.

Run the tests with `make test` (backend: pytest, frontend: vitest) and `make lint`.

## API

### `GET /api/resolve?q=<name or coordinates>[&refresh=true]`

Resolves the target and returns (see `backend/app/schemas/target.py`):

- `coordinates`: ICRS RA/Dec in degrees and sexagesimal, galactic l/b, and which service provided them
- `kinematics`: redshift `z`, recessional velocity `cz` in km/s, errors, measurement type
- `morphology`: morphological type (e.g. `SB(s)b`), SIMBAD object type and label, major/minor axis, PA
- `distances`: redshift-independent distances from SIMBAD's `mesDistance` table
- `environment`: cataloged group/cluster memberships (identifiers from FCC, VCC, LGG, HCG, Abell, ...)
  and galaxy groups/clusters/pairs found by a 1 degree SIMBAD cone search
- `aliases`, `sources`, `warnings`, `suggested_fov_deg`

Accepted inputs: any SIMBAD/NED identifier, decimal degrees (`53.40 -36.14`), sexagesimal
(`03h33m36.4s -36d08m25s`, `03:33:36.4 -36:08:25`, `03 33 36.4 -36 08 25`) or compact IAU form
(`J033336.4-360825`). Coordinates are matched to the nearest SIMBAD object within 30 arcsec.

Resolution strategy: SIMBAD TAP (explicit ADQL via pyvo) is the primary source; NED provides an
independent name/redshift and is the position fallback; CDS Sesame is the last-resort position
fallback. Every remote call is isolated, so an outage of one service appears in `warnings` instead
of failing the request. Results are cached in memory for `ASTROSCOPE_CACHE_TTL` seconds.

### `GET /api/surveys`

The HiPS surveys offered per pane, the coverage (MOC) overlays, and the default 2x2 layout.
Edit `backend/app/services/surveys.py` to change them.

## Viewer synchronisation

Aladin Lite v3 has no built-in view linking, so `frontend/src/lib/viewSync.ts` implements it on
top of the public callbacks: each pane reports `positionChanged` / `zoomChanged`, and the
controller pushes the new centre and field of view to the other panes with `gotoRaDec` /
`setFoV`. Programmatic writes echo back through the same callbacks (sometimes synchronously,
sometimes from the render loop), so the controller mutes a pane while writing to it and then
drops callbacks that merely repeat the last state it pushed. A toggle disables sync; re-enabling
snaps all panes to the pane that was navigated last.

## Configuration

See `.env.example`. Keys for ADS and the LLM provider are read but not used until modules 5-6.

## Notes for verification

The development sandbox used to build this could not reach CDS, SIMBAD or NED, so the resolver
is tested against faked service responses. The first live run should confirm:

1. `GET /api/resolve?q=NGC%201365` returns `main_id = "NGC  1365"`, z ~ 0.0055, type `SB(s)b`,
   and `FCC 121` under environment memberships.
2. The MOC overlay URLs in `surveys.py` resolve on the CDS MOC server (adjust the IDs if not).
