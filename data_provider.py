"""
AMDALens - Data provider (single source of truth for the dashboard).

The app never hardcodes numbers. It asks here, and gets REAL satellite-derived
values either from:
  - `precomputed.json` (default) -> instant, consistent, works offline; or
  - a live Google Earth Engine run (live toggle / uploaded polygon), cached.

This keeps the demo credible (real data) AND robust for a live presentation
(no dependency on venue wifi for the built-in demo polygons).
"""
import json
from pathlib import Path

import streamlit as st

PRECOMPUTED_PATH = Path(__file__).parent / "precomputed.json"


@st.cache_data(show_spinner=False)
def load_precomputed() -> dict:
    """Load baked-in real baselines for the demo polygons."""
    if PRECOMPUTED_PATH.exists():
        try:
            return json.loads(PRECOMPUTED_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def get_precomputed(demo_key: str):
    """Real precomputed baseline for a demo polygon, or None if missing."""
    return load_precomputed().get(demo_key)


@st.cache_data(show_spinner=False, ttl=3600)
def compute_live(key: str, geom_json: str, meta_json: str = None) -> dict:
    """
    Live GEE compute for a polygon (uploads / live toggle). Cached by geometry.
    Requires Earth Engine to be initialized already (see app.init_gee).
    Raises on failure; the caller handles the fallback/message.
    """
    import ee
    from baseline import build_baseline
    geom = ee.Geometry(json.loads(geom_json))
    meta = json.loads(meta_json) if meta_json else {}
    return build_baseline(key, geom, meta, source="live")


def get_baseline(demo_key: str, geom_geojson: dict = None, meta: dict = None,
                 live: bool = False):
    """
    Return a baseline dict (schema from baseline.build_baseline).

    - demo polygon + not live -> precomputed (instant, real).
    - demo polygon + live      -> recompute via GEE (cached).
    - custom upload (always live) -> compute via GEE (cached).
    """
    if not live and demo_key in ("morowali", "reference"):
        pc = get_precomputed(demo_key)
        if pc is not None:
            return pc
    geom_json = json.dumps(geom_geojson) if geom_geojson else None
    meta_json = json.dumps(meta) if meta else None
    return compute_live(demo_key, geom_json, meta_json)
