"""
AMDALens - Configuration
Konstanta aplikasi, styling, dan konfigurasi GEE.
"""

# ============ BRANDING ============
APP_TITLE = "AMDALens"
APP_SUBTITLE = "Platform Intelijen Verifikasi AMDAL Berbasis Satelit"
APP_TAGLINE = "Mendorong Kepatuhan Lingkungan dan Pencegahan Deforestasi di Indonesia"

# ============ COLORS ============
COLOR_PRIMARY = "#1F4E79"
COLOR_ACCENT = "#2E75B6"
COLOR_SUCCESS = "#2E7D32"
COLOR_WARNING = "#C77700"
COLOR_DANGER = "#B00020"
COLOR_MUTED = "#595959"
COLOR_SOFT = "#E7F0FA"

# ============ RISK SCORING ============
# Bobot Skor Risiko Dampak Lingkungan (sesuai proposal)
WEIGHTS = {
    "IPTH": 0.30,  # Indeks Perubahan Tutupan Hutan
    "IKH":  0.25,  # Indeks Kerentanan Hidrologi
    "ISR":  0.20,  # Indeks Slope Risk
    "IKKL": 0.15,  # Indeks Kedekatan Kawasan Lindung
    "ISB":  0.10,  # Indeks Sensitivitas Biodiversitas
}

# Klasifikasi skor (batas atas inklusif pada kelas sebelumnya)
# 0-40 AMAN, 40.01-70 WASPADA, 70.01-100 KRITIS
def classify_risk(score: float):
    """Return (label, color, status_text) for a given score 0-100."""
    if score <= 40:
        return "AMAN", COLOR_SUCCESS, "Risiko Rendah"
    if score <= 70:
        return "WASPADA", COLOR_WARNING, "Risiko Menengah"
    if score <= 100:
        return "KRITIS", COLOR_DANGER, "Risiko Tinggi"
    return "UNKNOWN", COLOR_MUTED, "Status Tidak Diketahui"


# ============ GEE DATASETS ============
DATASETS = {
    "sentinel2":     "COPERNICUS/S2_SR_HARMONIZED",
    "dynamic_world": "GOOGLE/DYNAMICWORLD/V1",
    "hansen":        "UMD/hansen/global_forest_change_2023_v1_11",
    "worldcover":    "ESA/WorldCover/v200/2021",
    "srtm":          "USGS/SRTMGL1_003",
    "jrc_water":     "JRC/GSW1_4/GlobalSurfaceWater",
    "wdpa":          "WCMC/WDPA/current/polygons",
}

# ============ ANALYSIS PARAMETERS ============
BASELINE_YEAR = 2019   # Tahun baseline (sebelum ekspansi signifikan)
CURRENT_YEAR  = 2025   # Tahun perbandingan
BUFFER_METERS = 1000   # Buffer 1 km di sekitar polygon untuk IPTH

# Cloud cover threshold untuk Sentinel-2 (addressing "cloud cover" concern)
MAX_CLOUD_COVER = 20   # %

# Dynamic World: mapping probability band to classes
DW_CLASSES = {
    0: "Water",
    1: "Trees",
    2: "Grass",
    3: "Flooded vegetation",
    4: "Crops",
    5: "Shrub & Scrub",
    6: "Built area",
    7: "Bare ground",
    8: "Snow & Ice",
}

DW_COLORS = [
    "#419BDF",  # 0 water
    "#397D49",  # 1 trees
    "#88B053",  # 2 grass
    "#7A87C6",  # 3 flooded vegetation
    "#E49635",  # 4 crops
    "#DFC35A",  # 5 shrub & scrub
    "#C4281B",  # 6 built
    "#A59B8F",  # 7 bare
    "#B39FE1",  # 8 snow & ice
]

# ============ DEMO MESSAGE ============
DISCLAIMER = (
    "AMDALens adalah alat pendukung keputusan (decision-support tool), "
    "bukan penentu legal. Hasil analisis digunakan untuk memperkaya, bukan "
    "menggantikan, proses penilaian oleh Komisi Penilai AMDAL (KPA) dan "
    "verifikasi lapangan resmi."
)
