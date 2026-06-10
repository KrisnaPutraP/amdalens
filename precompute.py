"""
AMDALens - Precompute real satellite baselines for the demo polygons.

Runs the Google Earth Engine pipeline ONCE for each demo polygon and writes the
real, satellite-derived numbers to `precomputed.json`. The app reads that file by
default, so the dashboard always shows REAL and CONSISTENT figures, instantly,
even with no internet at the venue. Re-run whenever you want to refresh.

Usage:
    venv/Scripts/python precompute.py            # both demo polygons -> json
    venv/Scripts/python precompute.py --print    # compute & print, don't write
"""
import json
import sys

import ee

from baseline import build_baseline
from sample_polygons import get_demo_polygon


def _init_ee():
    """Initialize EE from the local service-account secrets (BOM-safe)."""
    try:
        import tomllib
        txt = open(".streamlit/secrets.toml", encoding="utf-8-sig").read()
        sa = tomllib.loads(txt)["gee_service_account"]
    except Exception as e:
        print(f"FATAL: cannot read .streamlit/secrets.toml ({e})")
        sys.exit(1)
    creds = ee.ServiceAccountCredentials(
        email=sa["client_email"], key_data=json.dumps(sa)
    )
    ee.Initialize(creds, project=sa.get("project_id"))
    print(f"EE ready (project {sa.get('project_id')})")


def main():
    write = "--print" not in sys.argv
    _init_ee()
    out = {}
    for key in ("morowali", "reference"):
        geom_geojson, meta = get_demo_polygon(key)
        print(f"\n=== {key} ({meta['name']}) ===")
        b = build_baseline(key, ee.Geometry(geom_geojson), meta,
                           source="precomputed", log=print)
        s = b["score"]
        print(f"  -> sub-indices: {s['sub_indices']}")
        print(f"  -> SKOR {s['total']:.1f}/100  {s['label']} "
              f"(tertimbang {s['weighted_total']}, dampak-terealisasi "
              f"{s['realized_impact']})")
        out[key] = b

    if write:
        with open("precomputed.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)
        print("\nWrote precomputed.json")
    else:
        print("\n(--print: not written)")


if __name__ == "__main__":
    main()
