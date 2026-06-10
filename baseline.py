"""
AMDALens - Shared baseline builder.

Runs the Google Earth Engine pipeline for ONE geometry and assembles the full
baseline dict (landcover now + baseline year, slope, hydrology, tree loss,
protected-area distance, NDVI series) plus the computed risk score.

Used by both `precompute.py` (CLI, demo polygons) and `data_provider.py`
(live / uploaded polygons). No Streamlit dependency, so it runs headless too.
"""
import time
from datetime import date

import ee

import gee_pipeline as gp
from config import DW_CLASSES, BASELINE_YEAR, CURRENT_YEAR
from risk_engine import score_from_baseline

# Prior sensitivitas biodiversitas per area (proxy MVP; produksi: IUCN + KBA).
BIODIVERSITY_PRIOR = {
    "morowali":  {"score": 78, "source": "Prior regional Wallacea (hotspot)"},
    "reference": {"score": 68, "source": "Prior regional Sulawesi (benchmark)"},
}
DEFAULT_BIODIVERSITY = {"score": 60, "source": "Prior regional default (Indonesia)"}


def named_landcover(raw: dict) -> dict:
    """Map Dynamic World class ints -> human names, sorted desc by %."""
    named = {DW_CLASSES.get(int(k), str(k)): v for k, v in (raw or {}).items()}
    return dict(sorted(named.items(), key=lambda kv: kv[1], reverse=True))


def _safe(label, fn, default, log=None):
    """Run one pipeline call; never let a single failure abort the whole build."""
    t = time.time()
    try:
        r = fn()
        if log:
            log(f"  [ok {time.time()-t:4.1f}s] {label}")
        return r
    except Exception as e:
        if log:
            log(f"  [FAIL {time.time()-t:4.1f}s] {label}: {e}")
        return default


def build_baseline(key: str, geom: "ee.Geometry", meta: dict = None,
                   source: str = "live", log=None) -> dict:
    """Run the full pipeline for `geom` and return the baseline+score dict."""
    meta = meta or {}
    lc_cur = named_landcover(_safe(
        f"landcover {CURRENT_YEAR}",
        lambda: gp.get_landcover_summary(geom, CURRENT_YEAR), {}, log))
    lc_base = named_landcover(_safe(
        f"landcover {BASELINE_YEAR}",
        lambda: gp.get_landcover_summary(geom, BASELINE_YEAR), {}, log))
    slope = _safe("slope", lambda: gp.get_elevation_slope_summary(geom), {}, log)
    water = _safe("water", lambda: gp.get_water_distance_summary(geom), {}, log)
    river = _safe("river proximity", lambda: gp.get_river_proximity(geom), {}, log)
    water = {**water, **river}
    tree_loss = _safe("tree loss", lambda: gp.get_tree_loss_summary(geom), {}, log)
    protected = _safe("protected distance",
                      lambda: gp.get_protected_distance(geom),
                      {"distance_km": None, "overlap": False,
                       "source": "WDPA (gagal)"}, log)
    ndvi = _safe("ndvi timeseries",
                 lambda: gp.get_ndvi_timeseries(geom, 2019, CURRENT_YEAR), [], log)
    area_km2 = _safe("area",
                     lambda: round(geom.area(1).divide(1e6).getInfo(), 1),
                     meta.get("approx_area_km2"), log)

    baseline = {
        "key": key,
        "meta": meta,
        "source": source,
        "computed_at": date.today().isoformat(),
        "year_baseline": BASELINE_YEAR,
        "year_current": CURRENT_YEAR,
        "area_km2": area_km2,
        "landcover": lc_cur,
        "landcover_baseline": lc_base,
        "slope": slope,
        "water": water,
        "tree_loss": tree_loss,
        "protected": protected,
        "biodiversity": BIODIVERSITY_PRIOR.get(key, DEFAULT_BIODIVERSITY),
        "ndvi": ndvi,
    }
    score = score_from_baseline(baseline)
    baseline["subindices"] = score["sub_indices"]
    baseline["score"] = score
    return baseline
