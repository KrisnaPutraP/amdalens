"""
AMDALens - pre-flight health check.

Run this ~5 minutes before presenting LIVE to confirm everything is green:
  - precomputed.json is present and sane (demo works even with no internet),
  - the Google Earth Engine service account authenticates and can query,
  - secrets.toml has no BOM (Streamlit's st.secrets loader breaks on a BOM).

    venv/Scripts/python healthcheck.py

Exit code 0 = all good; non-zero = something needs attention.
"""
import json
import sys
import time


def main():
    ok = True

    # 1) precomputed.json present & sane -> the demo always works offline.
    try:
        d = json.load(open("precomputed.json", encoding="utf-8"))
        for k in ("morowali", "reference"):
            s = d[k]["score"]
            print(f"[precomputed] {k:10}: {s['total']:>5}/100  {s['label']}")
    except Exception as e:
        print("[precomputed] FAIL:", e)
        ok = False

    # 2) secrets.toml BOM check (Streamlit's toml loader chokes on a BOM).
    try:
        raw = open(".streamlit/secrets.toml", "rb").read()
        if raw[:3] == b"\xef\xbb\xbf":
            print("[secrets]     WARNING: secrets.toml has a BOM -> st.secrets will "
                  "fail. Re-save as UTF-8 WITHOUT BOM.")
            ok = False
        else:
            print("[secrets]     OK - no BOM")
    except Exception as e:
        print("[secrets]     FAIL:", e)
        ok = False

    # 3) GEE auth + a real query.
    try:
        import ee
        import tomllib
        sa = tomllib.loads(
            open(".streamlit/secrets.toml", encoding="utf-8-sig").read()
        )["gee_service_account"]
        t = time.time()
        ee.Initialize(
            ee.ServiceAccountCredentials(sa["client_email"],
                                         key_data=json.dumps(sa)),
            project=sa.get("project_id"),
        )
        n = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
             .filterDate("2025-01-01", "2025-12-31")
             .filterBounds(ee.Geometry.Point([122.15, -2.84]))
             .size().getInfo())
        print(f"[GEE]         OK in {time.time()-t:4.1f}s - Sentinel-2 reachable "
              f"(n={n}) as {sa['client_email']}")
    except Exception as e:
        print("[GEE]         FAIL:", repr(e)[:200])
        print("              (Demo polygons still work via precomputed.json; only "
              "live/upload needs GEE.)")
        ok = False

    print("\nALL GOOD - siap presentasi." if ok
          else "\nNEEDS ATTENTION - cek pesan di atas.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
