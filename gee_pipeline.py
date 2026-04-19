"""
AMDALens - Google Earth Engine Pipeline
Semua komputasi geospasial berat dijalankan di server Google (gratis untuk riset).
Modul ini hanya mengirim query dan menerima hasil agregat (angka atau URL tile).

Pattern: setiap fungsi menerima ee.Geometry, mengembalikan dict atau URL.
Semua fungsi dapat di-cache menggunakan @st.cache_data di app.py.
"""
import ee
from datetime import datetime
from config import DATASETS, BASELINE_YEAR, CURRENT_YEAR, BUFFER_METERS, MAX_CLOUD_COVER


# ============ INITIALIZATION ============
def initialize_ee(project_id: str = None, service_account_info: dict = None):
    """
    Initialize Earth Engine. Two modes:
      1. Local dev: ee.Authenticate() interactively, then ee.Initialize(project=...)
      2. Streamlit Cloud: use a service account (JSON in st.secrets)
    """
    if service_account_info:
        credentials = ee.ServiceAccountCredentials(
            email=service_account_info["client_email"],
            key_data=service_account_info_to_key_string(service_account_info)
        )
        ee.Initialize(credentials, project=project_id)
    else:
        try:
            ee.Initialize(project=project_id)
        except Exception:
            ee.Authenticate()
            ee.Initialize(project=project_id)


def service_account_info_to_key_string(info: dict) -> str:
    """Convert a service account dict to JSON string for EE credentials."""
    import json
    return json.dumps(info)


# ============ HELPERS ============
def geojson_to_ee_geometry(geojson_geom: dict) -> ee.Geometry:
    """Convert a GeoJSON geometry dict to ee.Geometry."""
    return ee.Geometry(geojson_geom)


def mask_s2_clouds(img):
    """Mask clouds using Sentinel-2 QA60 band. Simple but effective."""
    qa = img.select("QA60")
    cloud_bit_mask = 1 << 10
    cirrus_bit_mask = 1 << 11
    mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(
        qa.bitwiseAnd(cirrus_bit_mask).eq(0)
    )
    return img.updateMask(mask).divide(10000)


def get_s2_composite(geom: ee.Geometry, year: int):
    """Median composite Sentinel-2 untuk 1 tahun, dengan cloud masking."""
    start = f"{year}-01-01"
    end = f"{year}-12-31"
    collection = (
        ee.ImageCollection(DATASETS["sentinel2"])
        .filterBounds(geom)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUD_COVER))
        .map(mask_s2_clouds)
    )
    return collection.median().clip(geom)


def compute_ndvi(img):
    """NDVI = (NIR - RED) / (NIR + RED). Sentinel-2: B8=NIR, B4=RED."""
    return img.normalizedDifference(["B8", "B4"]).rename("NDVI")


# ============ AUTO-BASELINE ============
def get_landcover_summary(geom: ee.Geometry, year: int = CURRENT_YEAR) -> dict:
    """
    Klasifikasi tutupan lahan menggunakan Dynamic World V1.
    Returns: dict {class_name: percentage}.
    """
    start = f"{year}-01-01"
    end = f"{year}-12-31"
    dw = (
        ee.ImageCollection(DATASETS["dynamic_world"])
        .filterBounds(geom)
        .filterDate(start, end)
        .select("label")
        .mode()  # modus piksel (kelas paling sering)
        .clip(geom)
    )

    # Hitung persentase setiap kelas dengan reduceRegion
    hist = dw.reduceRegion(
        reducer=ee.Reducer.frequencyHistogram(),
        geometry=geom,
        scale=10,
        maxPixels=1e9,
    ).get("label")

    hist_dict = ee.Dictionary(hist).getInfo()
    if not hist_dict:
        return {}

    total = sum(hist_dict.values())
    result = {}
    for k, v in hist_dict.items():
        pct = (v / total) * 100 if total > 0 else 0
        result[int(k)] = round(pct, 2)
    return result


def get_elevation_slope_summary(geom: ee.Geometry) -> dict:
    """Kemiringan lereng dari SRTM DEM. Returns mean/max slope & % curam."""
    dem = ee.Image(DATASETS["srtm"]).clip(geom)
    slope = ee.Terrain.slope(dem).clip(geom)

    # Statistik slope
    stats = slope.reduceRegion(
        reducer=ee.Reducer.mean().combine(
            reducer2=ee.Reducer.max(), sharedInputs=True
        ),
        geometry=geom,
        scale=30,
        maxPixels=1e9,
    ).getInfo()

    # Persentase area curam (>30 derajat per pedoman KLHK)
    steep = slope.gt(30).rename("steep")
    steep_pct = steep.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geom,
        scale=30,
        maxPixels=1e9,
    ).getInfo()

    return {
        "mean_slope_deg": round(stats.get("slope_mean", 0) or 0, 2),
        "max_slope_deg": round(stats.get("slope_max", 0) or 0, 2),
        "steep_pct": round((steep_pct.get("steep", 0) or 0) * 100, 2),
    }


def get_water_distance_summary(geom: ee.Geometry) -> dict:
    """Analisis kedekatan ke permanent water bodies (JRC Global Surface Water)."""
    water = (
        ee.Image(DATASETS["jrc_water"])
        .select("occurrence")
        .gt(75)  # piksel yang >75% waktu berupa air dianggap badan air permanen
        .selfMask()
    )

    # Persentase piksel air dalam polygon
    water_in_poly = water.reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=geom,
        scale=30,
        maxPixels=1e9,
    ).getInfo()

    total_pixels = geom.area(1).divide(30 * 30).getInfo()
    water_count = water_in_poly.get("occurrence", 0) or 0
    water_pct = (water_count / total_pixels * 100) if total_pixels > 0 else 0

    return {
        "water_within_polygon_pct": round(water_pct, 3),
    }


def get_tree_loss_summary(geom: ee.Geometry) -> dict:
    """
    Hansen Global Forest Change: kehilangan tutupan hutan sejak 2000.
    Fokus pada tahun-tahun terbaru yang tersedia.
    """
    hansen = ee.Image(DATASETS["hansen"])
    tree_cover_2000 = hansen.select("treecover2000").gt(30)  # >30% canopy
    loss_year = hansen.select("lossyear")  # tahun loss (0=no loss, 1=2001, ...)

    # Buffer polygon 1 km untuk IPTH
    buffered = geom.buffer(BUFFER_METERS)

    # Total area tutupan hutan awal (2000)
    tree_area_2000 = tree_cover_2000.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=buffered,
        scale=30,
        maxPixels=1e9,
    ).getInfo()

    # Area loss dalam 5 tahun terakhir (loss year 18-23 = 2018-2023)
    # Hansen dataset version 2023_v1_11 mencakup hingga 2023
    recent_loss = loss_year.gte(18).And(loss_year.lte(23))
    recent_loss_area = recent_loss.multiply(ee.Image.pixelArea()).reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=buffered,
        scale=30,
        maxPixels=1e9,
    ).getInfo()

    tree_ha_2000 = (tree_area_2000.get("treecover2000", 0) or 0) / 10000
    loss_ha_recent = (recent_loss_area.get("lossyear", 0) or 0) / 10000

    loss_pct_recent = (loss_ha_recent / tree_ha_2000 * 100) if tree_ha_2000 > 0 else 0
    annual_loss_pct = loss_pct_recent / 6  # spread across 6 years

    return {
        "tree_cover_2000_ha": round(tree_ha_2000, 1),
        "loss_2018_2023_ha": round(loss_ha_recent, 2),
        "annual_loss_pct": round(annual_loss_pct, 2),
    }


def get_ndvi_timeseries(geom: ee.Geometry, start_year: int = 2019,
                        end_year: int = 2025) -> list:
    """
    Rata-rata NDVI tahunan di dalam polygon, untuk chart tren.
    Returns: list of {year, mean_ndvi}.
    """
    results = []
    for y in range(start_year, end_year + 1):
        start = f"{y}-01-01"
        end = f"{y}-12-31"
        coll = (
            ee.ImageCollection(DATASETS["sentinel2"])
            .filterBounds(geom)
            .filterDate(start, end)
            .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", MAX_CLOUD_COVER))
            .map(mask_s2_clouds)
            .map(compute_ndvi)
        )
        mean_img = coll.mean().clip(geom)
        mean_val = mean_img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=geom,
            scale=30,
            maxPixels=1e9,
        ).getInfo()
        results.append({
            "year": y,
            "mean_ndvi": round(mean_val.get("NDVI", 0) or 0, 4),
        })
    return results


# ============ TILE URLs FOR FOLIUM ============
def get_s2_tile_url(geom: ee.Geometry, year: int) -> str:
    """Return a Folium-compatible tile URL for RGB Sentinel-2 composite."""
    img = get_s2_composite(geom, year)
    vis = {"bands": ["B4", "B3", "B2"], "min": 0.0, "max": 0.3, "gamma": 1.2}
    map_id = img.getMapId(vis)
    return map_id["tile_fetcher"].url_format


def get_dw_tile_url(geom: ee.Geometry, year: int) -> str:
    """Return a tile URL for Dynamic World classification."""
    from config import DW_COLORS
    start = f"{year}-01-01"
    end = f"{year}-12-31"
    dw = (
        ee.ImageCollection(DATASETS["dynamic_world"])
        .filterBounds(geom)
        .filterDate(start, end)
        .select("label")
        .mode()
        .clip(geom)
    )
    vis = {"min": 0, "max": 8, "palette": DW_COLORS}
    map_id = dw.getMapId(vis)
    return map_id["tile_fetcher"].url_format


def get_loss_tile_url(geom: ee.Geometry) -> str:
    """Return tile URL for Hansen forest loss (bright red on dark basemap)."""
    hansen = ee.Image(DATASETS["hansen"])
    loss = hansen.select("lossyear").gte(18).selfMask()
    vis = {"palette": ["#FF2020"]}
    map_id = loss.getMapId(vis)
    return map_id["tile_fetcher"].url_format