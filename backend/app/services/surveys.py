"""Catalog of HiPS surveys and coverage overlays offered to the Aladin Lite viewer.

HiPS identifiers are the CDS ``P/...`` short IDs understood by Aladin Lite v3's
``setImageSurvey``/``A.imageHiPS``. Overlay MOCs are fetched by the browser directly.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Survey(BaseModel):
    id: str = Field(description="HiPS identifier accepted by Aladin Lite")
    label: str
    band: str = Field(description="Broad wavelength regime")
    description: str = ""
    cmap: str | None = Field(default=None, description="Suggested Aladin colormap for mono surveys")


class Overlay(BaseModel):
    id: str
    label: str
    moc_url: str = Field(description="URL of a MOC (FITS or JSON) describing the coverage")
    color: str
    description: str = ""


SURVEYS: list[Survey] = [
    Survey(
        id="P/DSS2/color",
        label="DSS2 colour",
        band="optical",
        description="Digitized Sky Survey 2, RGB composite",
    ),
    Survey(id="P/DSS2/red", label="DSS2 red", band="optical", cmap="grayscale"),
    Survey(
        id="P/PanSTARRS/DR1/color-z-zg-g",
        label="Pan-STARRS DR1 colour",
        band="optical",
        description="z / zg / g composite (Dec > -30)",
    ),
    Survey(id="P/PanSTARRS/DR1/g", label="Pan-STARRS DR1 g", band="optical", cmap="grayscale"),
    Survey(id="P/SDSS9/color", label="SDSS DR9 colour", band="optical"),
    Survey(id="P/DECaLS/DR5/color", label="DECaLS DR5 colour", band="optical"),
    Survey(id="P/DES-DR2/ColorIRG", label="DES DR2 colour", band="optical"),
    Survey(id="P/GALEXGR6/AIS/color", label="GALEX GR6 AIS (FUV+NUV)", band="ultraviolet"),
    Survey(id="P/GALEXGR6_7/NUV", label="GALEX GR6/7 NUV", band="ultraviolet", cmap="grayscale"),
    Survey(id="P/2MASS/color", label="2MASS J/H/K", band="near-infrared"),
    Survey(id="P/allWISE/color", label="AllWISE colour", band="mid-infrared"),
    Survey(id="P/unWISE/color-W2-W1W2-W1", label="unWISE W1/W2", band="mid-infrared"),
    Survey(
        id="P/Finkbeiner",
        label="Finkbeiner H-alpha",
        band="optical (narrow-band)",
        cmap="grayscale",
    ),
    Survey(id="P/XMM/EPIC-RGB", label="XMM-Newton EPIC", band="X-ray"),
    Survey(id="P/Fermi/color", label="Fermi LAT", band="gamma-ray"),
]

# Coverage overlays (MOCs). URLs point at the CDS MOCServer, which serves the coverage of any
# registered resource as a MOC. These were not reachable from the development sandbox, so the
# IDs below should be checked against https://alasky.cds.unistra.fr/MocServer/query?expr=... .
_MOCSERVER = "https://alasky.cds.unistra.fr/MocServer/query?ID={id}&get=moc&fmt=json"

OVERLAYS: list[Overlay] = [
    Overlay(
        id="hst",
        label="HST observations (footprints)",
        color="#38bdf8",
        moc_url=_MOCSERVER.format(id="CDS/B/hst/hstlog"),
        description="Coverage of the HST observation log (VizieR B/hst)",
    ),
    Overlay(
        id="jwst",
        label="JWST observations (footprints)",
        color="#f472b6",
        moc_url=_MOCSERVER.format(id="CDS/B/jwst/jwstlog"),
        description="Coverage of the JWST observation log (VizieR B/jwst)",
    ),
    Overlay(
        id="muse",
        label="ESO MUSE coverage",
        color="#a3e635",
        moc_url=_MOCSERVER.format(id="ESO/MUSE"),
        description="Coverage of public MUSE observations",
    ),
    Overlay(
        id="alma",
        label="ALMA coverage",
        color="#fb923c",
        moc_url=_MOCSERVER.format(id="ALMA/ALMA"),
        description="Coverage of public ALMA observations",
    ),
]

DEFAULT_GRID: list[str] = [
    "P/DSS2/color",
    "P/PanSTARRS/DR1/color-z-zg-g",
    "P/GALEXGR6/AIS/color",
    "P/2MASS/color",
]
