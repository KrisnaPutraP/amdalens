"""
AMDALens - Streamlit Dashboard
Platform Intelijen Verifikasi AMDAL Berbasis Satelit

Run:
    streamlit run app.py
"""
import streamlit as st
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from pathlib import Path

from config import (
    APP_TITLE, APP_SUBTITLE, APP_TAGLINE,
    COLOR_PRIMARY, COLOR_ACCENT, COLOR_SUCCESS, COLOR_WARNING, COLOR_DANGER,
    COLOR_MUTED, WEIGHTS,
    BASELINE_YEAR, CURRENT_YEAR, DISCLAIMER,
)
from sample_polygons import get_demo_polygon
from risk_engine import driver_narrative
from data_provider import get_baseline

# ============ UI THEME ============
TEXT_COLOR = "#17202A"
MUTED_TEXT = "#5C6675"
PAGE_BG = "#F5F7FA"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F1F6FA"
BORDER = "#D7E0EA"
SHADOW = "0 10px 26px rgba(31, 78, 121, 0.08)"
LOGO_PATH = Path("assets") / "amdalens-logo.jpeg"


def apply_plot_style(fig):
    """Keep Plotly charts readable even when Streamlit runs in dark mode."""
    axis_style = dict(
        gridcolor="#E2E8F0",
        linecolor=BORDER,
        zerolinecolor=BORDER,
        tickfont=dict(color=MUTED_TEXT),
        title_font=dict(color=TEXT_COLOR),
    )
    fig.update_layout(
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(color=TEXT_COLOR, family="Arial, sans-serif"),
        title_font=dict(color=TEXT_COLOR),
        xaxis=axis_style,
        yaxis=axis_style,
    )
    return fig


# ============ DATA HELPERS (real baseline -> UI) ============
def lc_get(baseline, name):
    """Percent for a Dynamic World class in the current-year landcover."""
    return float((baseline.get("landcover") or {}).get(name, 0.0))


def lc_base_get(baseline, name):
    """Percent for a class in the baseline-year landcover."""
    return float((baseline.get("landcover_baseline") or {}).get(name, 0.0))


def lc_delta(baseline, name):
    """Current - baseline percentage-point change for a class."""
    return round(lc_get(baseline, name) - lc_base_get(baseline, name), 1)


def fmt_delta_pp(d, baseline_year=None):
    """Format a percentage-point delta vs the baseline year for st.metric."""
    yr = baseline_year if baseline_year is not None else BASELINE_YEAR
    sign = "+" if d > 0 else ""
    return f"{sign}{d:.1f} poin vs {yr}"


def parse_uploaded_geometry(uploaded_file):
    """
    Parse an uploaded GeoJSON / KML / SHP(.zip) into (geojson_geom, meta) in
    EPSG:4326. Multiple/feature geometries are dissolved into one polygon.
    Raises ValueError on anything that isn't a usable polygon.
    """
    import json as _json
    from shapely.geometry import shape, mapping
    from shapely.ops import unary_union

    name = uploaded_file.name.lower()
    raw = uploaded_file.getvalue()
    geoms = []

    if name.endswith((".geojson", ".json")):
        gj = _json.loads(raw.decode("utf-8"))
        gtype = gj.get("type")
        if gtype == "FeatureCollection":
            geoms = [shape(f["geometry"]) for f in gj.get("features", [])
                     if f.get("geometry")]
        elif gtype == "Feature":
            geoms = [shape(gj["geometry"])]
        elif gtype in ("Polygon", "MultiPolygon", "GeometryCollection"):
            geoms = [shape(gj)]
    else:
        # SHP packaged as .zip, or .kml -> read via geopandas/fiona.
        import os
        import tempfile
        import geopandas as gpd
        suffix = ".zip" if name.endswith(".zip") else os.path.splitext(name)[1]
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(raw)
            path = tmp.name
        try:
            read_path = f"zip://{path}" if name.endswith(".zip") else path
            gdf = gpd.read_file(read_path)
            if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs(4326)
            geoms = [g for g in gdf.geometry if g is not None]
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass

    if not geoms:
        raise ValueError("Tidak ada geometri ditemukan dalam file.")

    g = unary_union(geoms)
    if not g.is_valid:
        g = g.buffer(0)  # fix self-intersections / topology
    if g.geom_type not in ("Polygon", "MultiPolygon"):
        raise ValueError(f"Geometri bukan polygon (tipe: {g.geom_type}).")

    c = g.centroid
    meta = {
        "name": f"Upload: {uploaded_file.name}",
        "province": "—", "district": "—", "subdistrict": "—",
        "proj_type_hypothesis": "Polygon diunggah pengguna",
        "center_lat": round(c.y, 4), "center_lon": round(c.x, 4),
        "approx_area_km2": None,
        "note": ("Polygon diunggah pengguna, dianalisis langsung (live) via "
                 "Google Earth Engine."),
    }
    return mapping(g), meta


# ============ PAGE CONFIG ============
st.set_page_config(
    page_title=f"{APP_TITLE} - AMDAL Intelligence Layer",
    page_icon=str(LOGO_PATH),
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============ GLOBAL STYLE ============
st.markdown(f"""
<style>
    :root {{
        --amdalens-text: {TEXT_COLOR};
        --amdalens-muted: {MUTED_TEXT};
        --amdalens-bg: {PAGE_BG};
        --amdalens-surface: {SURFACE};
        --amdalens-surface-alt: {SURFACE_ALT};
        --amdalens-border: {BORDER};
        --amdalens-shadow: {SHADOW};
    }}

    .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stHeader"] {{
        background: var(--amdalens-bg) !important;
        color: var(--amdalens-text) !important;
    }}

    [data-testid="stHeader"] {{
        background: rgba(255, 255, 255, 0.98) !important;
        border-bottom: 1px solid var(--amdalens-border);
        box-shadow: 0 2px 12px rgba(31, 78, 121, 0.08);
        color: var(--amdalens-text) !important;
    }}

    header[data-testid="stHeader"],
    header[data-testid="stHeader"] > div {{
        background: rgba(255, 255, 255, 0.98) !important;
    }}

    #MainMenu,
    [data-testid="stToolbar"] {{
        display: none !important;
        visibility: hidden !important;
    }}

    [data-testid="stToolbarActions"],
    [data-testid="stStatusWidget"],
    [data-testid="manage-app-button"],
    [data-testid="stDeployButton"],
    a[href*="share.streamlit.io"],
    button[title="View app source"],
    button[title="Edit app"],
    button[title="Deploy"],
    button[title="Share"],
    button[aria-label="View app source"],
    button[aria-label="Edit app"],
    button[aria-label="Deploy"],
    button[aria-label="Share"] {{
        display: none !important;
        visibility: hidden !important;
    }}

    [data-testid="stToolbar"] *,
    [data-testid="stToolbar"] button,
    [data-testid="stToolbar"] svg,
    header[data-testid="stHeader"] *,
    header[data-testid="stHeader"] button,
    header[data-testid="stHeader"] svg {{
        color: var(--amdalens-text) !important;
        fill: var(--amdalens-text) !important;
        stroke: var(--amdalens-text) !important;
    }}

    [data-testid="stDecoration"] {{
        background: linear-gradient(90deg, #B00020 0%, #1F4E79 50%, #C77700 100%) !important;
        height: 3px !important;
    }}

    /* Sidebar collapse / expand chevron: keep it dark & visible (was light-on-light) */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="collapsedControl"] {{
        visibility: visible !important;
        opacity: 1 !important;
    }}

    [data-testid="stSidebarCollapseButton"] svg,
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="stSidebarCollapsedControl"] svg,
    [data-testid="collapsedControl"] svg,
    [data-testid="stSidebarHeader"] svg,
    [data-testid="stSidebar"] button[kind="header"] svg {{
        color: {COLOR_PRIMARY} !important;
        fill: {COLOR_PRIMARY} !important;
        stroke: {COLOR_PRIMARY} !important;
        opacity: 1 !important;
    }}

    .main .block-container {{
        max-width: 1280px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }}

    [data-testid="stMarkdownContainer"],
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] strong,
    [data-testid="stMarkdownContainer"] em,
    [data-testid="stMarkdownContainer"] h1,
    [data-testid="stMarkdownContainer"] h2,
    [data-testid="stMarkdownContainer"] h3,
    [data-testid="stMarkdownContainer"] h4,
    [data-testid="stMarkdownContainer"] h5,
    [data-testid="stMarkdownContainer"] h6 {{
        color: var(--amdalens-text);
    }}

    [data-testid="stCaptionContainer"],
    [data-testid="stCaptionContainer"] p {{
        color: var(--amdalens-muted) !important;
    }}

    hr {{
        border-color: var(--amdalens-border) !important;
        margin: 1.5rem 0;
    }}

    .main-title {{
        font-size: 2.8rem;
        font-weight: 800;
        color: #0B4F6C;
        margin-bottom: 0;
        padding-bottom: 0;
        line-height: 1.05;
    }}

    .subtitle {{
        font-size: 1.15rem;
        color: #1D6F8A;
        font-style: italic;
        margin-top: 0.15rem;
        padding-top: 0;
    }}

    .tagline {{
        color: var(--amdalens-muted);
        font-size: 0.98rem;
        margin-top: 0.25rem;
    }}

    .score-card {{
        background: linear-gradient(135deg, var(--amdalens-surface-alt) 0%, var(--amdalens-surface) 100%);
        color: var(--amdalens-text);
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid var(--amdalens-border);
        border-left: 6px solid {COLOR_PRIMARY};
        box-shadow: var(--amdalens-shadow);
        margin: 1rem 0;
    }}

    .score-big {{ font-size: 4rem; font-weight: 700; line-height: 1; }}

    .score-label {{
        font-size: 1.4rem;
        font-weight: 700;
        letter-spacing: 0;
    }}

    .metric-chip {{
        background: var(--amdalens-surface-alt);
        color: var(--amdalens-text);
        padding: 0.3rem 0.7rem;
        border-radius: 8px;
        display: inline-block;
        margin: 0.2rem;
        font-size: 0.85rem;
    }}

    .alert-box {{
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border: 1px solid #F2B8B5;
        border-left: 5px solid {COLOR_DANGER};
        background: #FFF7F7;
        color: var(--amdalens-text);
    }}

    .alert-box p {{
        color: var(--amdalens-text);
    }}

    .finding-row {{
        background: var(--amdalens-surface);
        border: 1px solid var(--amdalens-border);
        border-left: 5px solid {COLOR_ACCENT};
        border-radius: 8px;
        color: var(--amdalens-text);
        margin: 0.75rem 0;
        padding: 0.85rem 1rem;
    }}

    .finding-row.critical {{
        border-left-color: {COLOR_DANGER};
        background: #FFF7F7;
    }}

    .finding-row.warning {{
        border-left-color: {COLOR_WARNING};
        background: #FFFBEB;
    }}

    .finding-row.success {{
        border-left-color: {COLOR_SUCCESS};
        background: #F0FDF4;
    }}

    .finding-label {{
        color: var(--amdalens-text);
        display: block;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0;
        margin-bottom: 0.35rem;
        text-transform: uppercase;
    }}

    .formula-box {{
        background: #FFFFFF;
        border: 1px solid var(--amdalens-border);
        border-radius: 8px;
        color: var(--amdalens-text);
        padding: 0.85rem;
    }}

    .formula-title {{
        color: var(--amdalens-text);
        font-size: 0.86rem;
        font-weight: 800;
        margin-bottom: 0.65rem;
    }}

    .formula-row {{
        border-top: 1px solid #E6EDF3;
        display: grid;
        gap: 0.35rem;
        grid-template-columns: 5.5rem minmax(0, 1fr);
        padding: 0.55rem 0;
    }}

    .formula-row:first-of-type {{
        border-top: 0;
    }}

    .formula-weight {{
        color: #0B4F6C;
        font-family: Arial, sans-serif;
        font-size: 0.82rem;
        font-weight: 800;
        white-space: nowrap;
    }}

    .formula-name {{
        color: var(--amdalens-text);
        font-size: 0.82rem;
        line-height: 1.35;
        min-width: 0;
        overflow-wrap: anywhere;
    }}

    .info-box {{
        padding: 0.9rem;
        border-radius: 8px;
        margin: 0.75rem 0;
        border: 1px solid #BBD1E8;
        border-left: 4px solid {COLOR_ACCENT};
        background: #EDF6FF;
        color: var(--amdalens-text);
        font-size: 0.85rem;
    }}

    .disclaimer {{
        font-size: 0.82rem;
        color: var(--amdalens-muted);
        font-style: italic;
        padding: 0.75rem;
        background: var(--amdalens-surface);
        border: 1px solid var(--amdalens-border);
        border-radius: 8px;
    }}

    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #FFFFFF 0%, #F6F9FC 100%) !important;
        border-right: 1px solid var(--amdalens-border);
    }}

    [data-testid="stSidebar"] * {{
        color: var(--amdalens-text) !important;
    }}

    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {{
        color: var(--amdalens-muted) !important;
    }}

    div[role="radiogroup"] label {{
        background: var(--amdalens-surface);
        border: 1px solid var(--amdalens-border);
        border-radius: 8px;
        padding: 0.55rem 0.75rem;
        margin-bottom: 0.45rem;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.35rem;
        border-bottom: 1px solid var(--amdalens-border);
        overflow-x: auto;
    }}

    .stTabs [data-baseweb="tab"] {{
        height: auto;
        padding: 0.7rem 0.85rem;
        border-radius: 8px 8px 0 0;
        background: #EAF1F7;
        color: var(--amdalens-muted);
        border: 1px solid transparent;
        border-bottom: 0;
        font-weight: 700;
        white-space: normal;
    }}

    .stTabs [data-baseweb="tab"] p {{
        color: inherit !important;
        font-size: 0.92rem;
    }}

    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        background: var(--amdalens-surface);
        color: {COLOR_DANGER};
        border-color: var(--amdalens-border);
    }}

    .stTabs [data-baseweb="tab-highlight"] {{
        background-color: {COLOR_DANGER};
        height: 3px;
    }}

    [data-testid="stMetric"] {{
        background: var(--amdalens-surface);
        border: 1px solid var(--amdalens-border);
        border-radius: 8px;
        padding: 0.9rem 1rem;
        box-shadow: var(--amdalens-shadow);
    }}

    [data-testid="stMetricLabel"],
    [data-testid="stMetricLabel"] *,
    [data-testid="stMetricValue"],
    [data-testid="stMetricValue"] * {{
        color: var(--amdalens-text) !important;
    }}

    [data-testid="stMetricDelta"],
    [data-testid="stMetricDelta"] * {{
        color: #9A3412 !important;
    }}

    [data-testid="stAlert"] {{
        border-radius: 8px;
        color: var(--amdalens-text) !important;
    }}

    [data-testid="stAlert"] * {{
        color: var(--amdalens-text) !important;
    }}

    [data-testid="stExpander"] {{
        background: var(--amdalens-surface);
        border: 1px solid var(--amdalens-border);
        border-radius: 8px;
    }}

    [data-testid="stExpander"] * {{
        color: var(--amdalens-text) !important;
    }}

    [data-testid="stCodeBlock"],
    [data-testid="stCodeBlock"] pre {{
        background: #FFFFFF !important;
        border-radius: 8px !important;
    }}

    [data-testid="stCodeBlock"] pre {{
        border: 1px solid var(--amdalens-border) !important;
        padding: 0.9rem 1rem !important;
    }}

    [data-testid="stCodeBlock"] code,
    [data-testid="stCodeBlock"] span {{
        background: transparent !important;
        color: var(--amdalens-text) !important;
        font-size: 0.86rem !important;
        line-height: 1.55 !important;
        text-shadow: none !important;
    }}

    pre,
    code {{
        color: var(--amdalens-text) !important;
    }}

    [data-testid="stPlotlyChart"],
    [data-testid="stDataFrame"],
    iframe {{
        background: var(--amdalens-surface);
        border: 1px solid var(--amdalens-border) !important;
        border-radius: 8px;
        box-shadow: var(--amdalens-shadow);
    }}

    textarea,
    input,
    [data-baseweb="select"] > div {{
        background: var(--amdalens-surface) !important;
        color: var(--amdalens-text) !important;
        border-color: var(--amdalens-border) !important;
        border-radius: 8px !important;
    }}

    label,
    [data-testid="stWidgetLabel"] p {{
        color: var(--amdalens-text) !important;
        font-weight: 600;
    }}

    .stButton > button,
    .stDownloadButton > button {{
        border-radius: 8px;
        font-weight: 700;
    }}

    @media (max-width: 760px) {{
        .main .block-container {{
            padding-left: 1rem;
            padding-right: 1rem;
        }}

        .main-title {{
            font-size: 2.1rem;
        }}

        .subtitle {{
            font-size: 1rem;
        }}

        .score-big {{
            font-size: 3rem;
        }}

        .stTabs [data-baseweb="tab"] {{
            padding: 0.55rem 0.65rem;
        }}
    }}
</style>
""", unsafe_allow_html=True)


# ============ GEE INITIALIZATION ============
def _load_service_account():
    """
    Service-account dict from st.secrets, falling back to a direct BOM-safe read
    of .streamlit/secrets.toml (Streamlit's own toml loader chokes on a BOM).
    """
    try:
        if "gee_service_account" in st.secrets:
            return dict(st.secrets["gee_service_account"])
    except Exception:
        pass
    local = Path.cwd() / ".streamlit" / "secrets.toml"
    if local.exists():
        try:
            import tomllib
            data = tomllib.loads(local.read_text(encoding="utf-8-sig"))
            return data.get("gee_service_account")
        except Exception:
            return None
    return None


@st.cache_resource
def init_gee():
    """Initialize Earth Engine from the service account. Returns (ok, error)."""
    try:
        import ee
        import json
        sa_info = _load_service_account()
        if sa_info:
            credentials = ee.ServiceAccountCredentials(
                email=sa_info["client_email"],
                key_data=json.dumps(sa_info),
            )
            ee.Initialize(credentials, project=sa_info.get("project_id"))
        else:
            ee.Initialize()  # local `earthengine authenticate` fallback
        return True, None
    except Exception as e:
        return False, str(e)


# ============ HEADER ============
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.image(str(LOGO_PATH), width=130)
with col_title:
    st.markdown(f"<div class='main-title'>{APP_TITLE}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='subtitle'>{APP_SUBTITLE}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='tagline'>{APP_TAGLINE}</div>", unsafe_allow_html=True)

st.markdown("---")


# ============ SIDEBAR ============
with st.sidebar:
    st.markdown("### Pilih Area Analisis")

    polygon_choice = st.radio(
        "Area",
        options=["Morowali (Demo KRITIS)", "Reference Area (Demo AMAN)",
                 "Upload Polygon Sendiri"],
        index=0,
        help="Pilih polygon demo, atau unggah polygon proyek Anda untuk dianalisis live.",
    )

    uploaded_file = None
    if "Upload" in polygon_choice:
        uploaded_file = st.file_uploader(
            "Unggah polygon (GeoJSON / KML / SHP .zip)",
            type=["geojson", "json", "kml", "zip"],
            help="Batas lokasi proyek (IUP/HGU/IPPKH). Dihitung live via Google Earth Engine.",
        )

    st.markdown("---")
    st.markdown("### Mode Komputasi")

    use_live_gee = st.checkbox(
        "Live Google Earth Engine",
        value=False,
        help=("ON: hitung ulang real-time dari satelit (butuh internet). "
              "OFF: pakai hasil satelit yang sudah dihitung (instan) untuk polygon demo."),
    )

    st.markdown("---")
    st.markdown("### Skor Risiko Dampak Lingkungan")
    with st.expander("Lihat formula", expanded=True):
        st.markdown(
            """
            <div class="formula-box">
                <div class="formula-title">Skor tertimbang 5 sub-indeks</div>
                <div class="formula-row">
                    <span class="formula-weight">0.30 x IPTH</span>
                    <span class="formula-name">Perubahan Tutupan Hutan</span>
                </div>
                <div class="formula-row">
                    <span class="formula-weight">0.25 x IKH</span>
                    <span class="formula-name">Kerentanan Hidrologi</span>
                </div>
                <div class="formula-row">
                    <span class="formula-weight">0.20 x ISR</span>
                    <span class="formula-name">Slope Risk</span>
                </div>
                <div class="formula-row">
                    <span class="formula-weight">0.15 x IKKL</span>
                    <span class="formula-name">Kedekatan Kawasan Lindung</span>
                </div>
                <div class="formula-row">
                    <span class="formula-weight">0.10 x ISB</span>
                    <span class="formula-name">Sensitivitas Biodiversitas</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.caption(
            "Skor akhir = nilai tertinggi antara skor tertimbang dan **skor "
            "dampak terealisasi** (konversi lahan + kehilangan hutan), agar "
            "lahan yang sudah rusak parah tidak ter-dilusi faktor lokasi."
        )

    st.markdown("---")
    st.caption("Indonesia Aerospace Hackathon 2026")
    st.caption("AMDALens v0.2 MVP")


# ============ RESOLVE GEE READINESS (only when actually needed) ============
need_gee = use_live_gee or ("Upload" in polygon_choice and uploaded_file is not None)
gee_ready, gee_error = (False, None)
if need_gee:
    gee_ready, gee_error = init_gee()


# ============ POLYGON SELECTION ============
if "Morowali" in polygon_choice:
    geom_geojson, meta = get_demo_polygon("morowali")
    demo_key = "morowali"
elif "Reference" in polygon_choice:
    geom_geojson, meta = get_demo_polygon("reference")
    demo_key = "reference"
else:
    if uploaded_file is None:
        st.info("Unggah file polygon (GeoJSON / KML / SHP .zip) di sidebar untuk "
                "memulai, atau pilih salah satu polygon demo.")
        st.stop()
    try:
        geom_geojson, meta = parse_uploaded_geometry(uploaded_file)
        demo_key = "custom"
    except Exception as e:
        st.error(f"Gagal membaca polygon dari file: {e}")
        st.stop()


# ============ FETCH REAL BASELINE (precomputed by default, live on demand) ============
is_live = use_live_gee or demo_key == "custom"
if is_live and not gee_ready:
    if demo_key == "custom":
        st.error(f"Polygon upload memerlukan Google Earth Engine, namun GEE tidak "
                 f"tersedia: {gee_error}")
        st.info("Coba lagi saat ada koneksi internet, atau pilih polygon demo "
                "(hasil precomputed, tanpa internet).")
        st.stop()
    st.sidebar.warning("GEE live tidak tersedia — memakai hasil precomputed.")
    is_live = False

try:
    if is_live:
        with st.spinner("Menghitung baseline lingkungan dari citra satelit..."):
            baseline = get_baseline(demo_key, geom_geojson, meta, live=True)
    else:
        baseline = get_baseline(demo_key, geom_geojson, meta, live=False)
except Exception as e:
    if demo_key in ("morowali", "reference"):
        baseline = get_baseline(demo_key)  # precomputed safety net
        st.sidebar.warning("GEE gagal — memakai hasil precomputed.")
    else:
        st.error(f"Gagal menghitung baseline dari satelit: {e}")
        st.stop()

# Use the baseline's own metadata (keeps display consistent with what was scored).
meta = baseline.get("meta", meta) or meta
data_source = baseline.get("source", "precomputed")
st.sidebar.caption(
    ("🟢 Sumber data: **live GEE** (real-time)" if data_source == "live"
     else "🔵 Sumber data: **precomputed** (hasil satelit nyata, instan)")
)


# ============ TABS: 4 FITUR UTAMA + 1 BONUS ============
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "1. Area Proyek",
    "2. Auto-Baseline",
    "3. Skor Risiko",
    "4. Monitoring Perubahan",
    "5. Cross-Check Klaim AMDAL",
])


# ============================================================
# TAB 1: AREA PROYEK
# ============================================================
with tab1:
    st.markdown("## Area Proyek")
    st.markdown(
        "Pemrakarsa mengunggah polygon lokasi proyek (IUP, HGU, IPPKH, atau "
        "KLHS). Sistem memvalidasi topologi, menghitung luas, lalu menjalankan "
        "pipeline satelit. Pilih polygon demo atau unggah polygon Anda di sidebar."
    )

    poly_color = (COLOR_DANGER if demo_key == "morowali"
                  else COLOR_SUCCESS if demo_key == "reference" else COLOR_ACCENT)
    area_km2 = baseline.get("area_km2") or meta.get("approx_area_km2")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Folium map
        center = [meta["center_lat"], meta["center_lon"]]
        m = folium.Map(location=center, zoom_start=11,
                       tiles="OpenStreetMap", control_scale=True)

        # Add Esri satellite basemap
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery", name="Satellite", overlay=False, control=True
        ).add_to(m)

        # Add the polygon
        folium.GeoJson(
            geom_geojson,
            name="Area Proyek",
            style_function=lambda x, _c=poly_color: {
                "color": _c, "weight": 3, "fillColor": _c, "fillOpacity": 0.2,
            },
            tooltip=meta["name"],
        ).add_to(m)

        folium.LayerControl().add_to(m)
        st_folium(m, height=450, use_container_width=True, returned_objects=[])

    with col2:
        st.markdown("### Informasi Polygon")
        st.markdown(f"**Nama:** {meta['name']}")
        st.markdown(f"**Provinsi:** {meta['province']}")
        st.markdown(f"**Kabupaten:** {meta['district']}")
        st.markdown(f"**Kecamatan:** {meta['subdistrict']}")
        st.markdown(f"**Tipe Proyek (hipotesis):** {meta['proj_type_hypothesis']}")
        st.markdown(f"**Luas (dihitung satelit):** "
                    f"{area_km2:.1f} km²" if area_km2 else "**Luas:** —")
        st.markdown(f"**Centroid:** {meta['center_lat']:.3f}, {meta['center_lon']:.3f}")

        st.markdown(f"<div class='info-box'>{meta['note']}</div>", unsafe_allow_html=True)

    st.success("Polygon tervalidasi. Sistem siap menjalankan pipeline Auto-Baseline.")


# ============================================================
# TAB 2: AUTO-BASELINE
# ============================================================
with tab2:
    st.markdown("## Auto-Baseline Lingkungan")
    st.markdown(
        "Dalam hitungan menit, pipeline Google Earth Engine mengekstrak "
        "baseline lingkungan 5 tahun terakhir dari polygon proyek. "
        "Proses ini menggantikan pekerjaan konsultan yang biasanya memakan "
        "waktu 2 sampai 4 minggu."
    )

    yr_cur = baseline.get("year_current", CURRENT_YEAR)
    yr_base = baseline.get("year_baseline", BASELINE_YEAR)

    # ============ LAND COVER CLASSIFICATION (Dynamic World) ============
    st.markdown(f"### Klasifikasi Tutupan Lahan {yr_cur} (Dynamic World, 10 m)")

    lc_data = baseline.get("landcover", {})

    col_chart, col_stats = st.columns([2, 1])
    with col_chart:
        df_lc = pd.DataFrame({
            "Kelas": list(lc_data.keys()),
            "Persentase": [round(v, 1) for v in lc_data.values()],
        })
        # Color map matching DW classes
        class_color_map = {
            "Water": "#419BDF", "Trees": "#397D49", "Grass": "#88B053",
            "Flooded vegetation": "#7A87C6", "Crops": "#E49635",
            "Shrub & Scrub": "#DFC35A", "Built area": "#C4281B",
            "Bare ground": "#A59B8F", "Snow & Ice": "#B39FE1",
        }
        fig = px.bar(
            df_lc, x="Persentase", y="Kelas", orientation="h",
            color="Kelas", color_discrete_map=class_color_map,
            text=df_lc["Persentase"].apply(lambda v: f"{v}%"),
        )
        fig.update_layout(
            showlegend=False, height=350,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Persentase Area (%)", yaxis_title="",
        )
        apply_plot_style(fig)
        fig.update_yaxes(categoryorder="total ascending")
        fig.update_traces(textposition="outside", textfont=dict(color=TEXT_COLOR))
        st.plotly_chart(fig, use_container_width=True)

    with col_stats:
        st.markdown(f"**Perubahan {yr_base} → {yr_cur}**")
        # Tree loss is bad (delta default: negative=red); built/bare gain is bad (inverse).
        st.metric("Tree Cover", f"{lc_get(baseline, 'Trees'):.1f}%",
                  fmt_delta_pp(lc_delta(baseline, "Trees"), yr_base))
        st.metric("Built Area", f"{lc_get(baseline, 'Built area'):.1f}%",
                  fmt_delta_pp(lc_delta(baseline, "Built area"), yr_base),
                  delta_color="inverse")
        st.metric("Bare Ground", f"{lc_get(baseline, 'Bare ground'):.1f}%",
                  fmt_delta_pp(lc_delta(baseline, "Bare ground"), yr_base),
                  delta_color="inverse")

    st.caption("Sumber: Google/WRI Dynamic World V1 (klasifikasi 10 m, near real-time)")

    st.markdown("---")

    # ============ TOPOGRAPHY (SRTM) ============
    st.markdown("### Topografi dan Kemiringan Lereng (SRTM DEM 30 m)")

    slope = baseline.get("slope", {})
    slope_mean = slope.get("mean_slope_deg", 0) or 0
    slope_max = slope.get("max_slope_deg", 0) or 0
    steep_pct = slope.get("steep_pct", 0) or 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Kemiringan Rata-rata", f"{slope_mean:.1f}°")
    c2.metric("Kemiringan Maksimum", f"{slope_max:.1f}°")
    c3.metric("Area Curam (>30°)", f"{steep_pct:.1f}%",
              help="Per Pedoman KLHK, kemiringan >30° masuk kategori sangat curam")

    st.caption("Sumber: NASA SRTM DEM (30 m global elevation)")

    st.markdown("---")

    # ============ HIDROLOGI ============
    st.markdown("### Analisis Hidrologi (JRC Global Surface Water)")

    water = baseline.get("water", {})
    water_pct = water.get("water_within_polygon_pct", 0) or 0
    near_river = bool(water.get("near_river", False))
    nearest_m = water.get("nearest_water_m")
    if nearest_m is None:
        river_note = "Tidak ada badan air permanen dalam radius 2 km dari polygon."
    elif nearest_m <= 1:
        river_note = "Terdapat badan air permanen DI DALAM polygon (paparan langsung)."
    else:
        river_note = f"Badan air permanen terdekat ~{nearest_m:.0f} m dari polygon."

    c1, c2 = st.columns(2)
    c1.metric("Badan Air Permanen dalam Polygon", f"{water_pct:.2f}%")
    c2.metric("Kedekatan Air Permanen", "Dekat (<500 m)" if near_river else "Jauh",
              delta="HIGH RISK" if near_river else None,
              delta_color="inverse" if near_river else "off")
    st.caption(f"Catatan: {river_note}")
    st.caption("Sumber: European Commission JRC Global Surface Water (30 m, 1984 hingga sekarang)")

    st.markdown("---")

    # ============ KEDEKATAN KAWASAN LINDUNG ============
    st.markdown("### Kedekatan ke Kawasan Lindung")

    prot = baseline.get("protected", {})
    dist_km = prot.get("distance_km")
    overlap = bool(prot.get("overlap", False))
    if overlap:
        dist_label, dist_delta, dist_color = "Beririsan", "KRITIS", "inverse"
    elif dist_km is None:
        dist_label, dist_delta, dist_color = "> 30 km", "jauh", "off"
    else:
        dist_label = f"{dist_km:.1f} km"
        near = dist_km < 5
        dist_delta = "<5 km" if near else ">5 km"
        dist_color = "inverse" if near else "off"

    c1, c2 = st.columns(2)
    c1.metric("Jarak ke Kawasan Lindung Terdekat (WDPA)", dist_label,
              delta=dist_delta, delta_color=dist_color)
    c2.metric("Overlap dengan Kawasan Lindung", "Ya" if overlap else "Tidak",
              delta="KRITIS" if overlap else "Tidak overlap",
              delta_color="inverse" if overlap else "normal")
    st.caption(f"Sumber: WDPA Protected Planet — {prot.get('source', 'WDPA')}. "
               "Catatan: kawasan hutan KLHK (HL/HP) belum termasuk; jarak ini batas bawah.")


# ============================================================
# TAB 3: SKOR RISIKO
# ============================================================
with tab3:
    st.markdown("## Environmental Risk Score")
    st.markdown(
        "Skor Risiko Dampak Lingkungan menggabungkan lima sub-indeks tertimbang "
        "untuk menghasilkan angka tunggal 0 sampai 100. Skor ini dirancang "
        "sebagai alat pendukung keputusan (decision-support), bukan penentu legal."
    )

    # Real score from the satellite baseline (precomputed or live).
    result = baseline["score"]
    total = result["total"]
    label = result["label"]
    color = result["color"]
    status_text = result["status_text"]
    sub = result["sub_indices"]
    contribs = result["weighted_contributions"]

    # ============ BIG SCORE CARD ============
    col_score, col_radar = st.columns([1, 2])

    with col_score:
        st.markdown(f"""
        <div class='score-card' style='text-align: center; border-left-color: {color};'>
            <div style='color: {COLOR_MUTED}; font-size: 0.9rem; margin-bottom: 0.3rem;'>
                SKOR RISIKO DAMPAK LINGKUNGAN
            </div>
            <div class='score-big' style='color: {color};'>
                {total:.0f}<span style='font-size: 1.5rem; color: {COLOR_MUTED};'>/100</span>
            </div>
            <div class='score-label' style='color: {color};'>
                {label}
            </div>
            <div style='color: {MUTED_TEXT}; font-size: 0.9rem; margin-top: 0.4rem;'>
                {status_text}
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"**Interpretasi:** {driver_narrative(result)}")

        if result.get("escalated"):
            st.markdown(
                f"<div class='info-box'>⚠️ <b>Eskalasi dampak terealisasi.</b> "
                f"Skor tertimbang 5-faktor = {result['weighted_total']:.0f}, "
                f"tetapi <b>{result.get('converted_pct', 0):.0f}% lahan sudah "
                f"terkonversi</b> (built + bare). Skor akhir dinaikkan ke "
                f"<b>{total:.0f}</b> karena dampak lingkungan sudah nyata, bukan "
                f"sekadar potensi.</div>",
                unsafe_allow_html=True,
            )

    with col_radar:
        # Radar chart of sub-indices
        categories = list(sub.keys())
        values = list(sub.values())
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            fillcolor=f"rgba(46, 117, 182, 0.3)",
            line=dict(color=COLOR_PRIMARY, width=2),
            name="Sub-indeks",
        ))
        fig.update_layout(
            polar=dict(
                bgcolor=SURFACE,
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    gridcolor=BORDER,
                    linecolor=BORDER,
                    tickfont=dict(color=MUTED_TEXT),
                ),
                angularaxis=dict(
                    gridcolor=BORDER,
                    linecolor=BORDER,
                    tickfont=dict(color=TEXT_COLOR),
                ),
            ),
            showlegend=False, height=380,
            margin=dict(l=60, r=60, t=40, b=40),
            title="Breakdown Sub-Indeks (0 sampai 100)",
        )
        apply_plot_style(fig)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ============ DETAILED BREAKDOWN ============
    st.markdown("### Kontribusi Tertimbang Setiap Sub-Indeks")

    names = {
        "IPTH": "Perubahan Tutupan Hutan",
        "IKH":  "Kerentanan Hidrologi",
        "ISR":  "Slope Risk",
        "IKKL": "Kedekatan Kawasan Lindung",
        "ISB":  "Sensitivitas Biodiversitas",
    }

    df_bd = pd.DataFrame([
        {
            "Kode": code,
            "Sub-Indeks": names[code],
            "Nilai Mentah (0-100)": sub[code],
            "Bobot": f"{WEIGHTS[code]:.2f}",
            "Kontribusi Tertimbang": contribs[code],
        }
        for code in WEIGHTS.keys()
    ])

    fig_bar = px.bar(
        df_bd, x="Kontribusi Tertimbang", y="Sub-Indeks",
        orientation="h", color="Kontribusi Tertimbang",
        color_continuous_scale=[[0, COLOR_SUCCESS], [0.5, COLOR_WARNING], [1, COLOR_DANGER]],
        text="Kontribusi Tertimbang",
        range_color=[0, 30],
    )
    fig_bar.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig_bar.update_layout(
        height=280, margin=dict(l=10, r=10, t=20, b=10),
        coloraxis_showscale=False,
        xaxis_title="Kontribusi ke Skor Total (poin)", yaxis_title="",
    )
    apply_plot_style(fig_bar)
    st.plotly_chart(fig_bar, use_container_width=True)

    with st.expander("Lihat tabel detail perhitungan"):
        st.dataframe(df_bd, use_container_width=True, hide_index=True)
        st.markdown(f"**Total: {total:.1f} / 100 - {label} ({status_text})**")

    # ============ DISCLAIMER ============
    st.markdown(f"<div class='disclaimer'>{DISCLAIMER}</div>", unsafe_allow_html=True)


# ============================================================
# TAB 4: MONITORING PERUBAHAN
# ============================================================
with tab4:
    st.markdown("## Compliance Monitoring: Before vs After")
    st.markdown(
        f"Perbandingan kondisi lingkungan antara tahun baseline ({yr_base}) dan "
        f"terkini ({yr_cur}), seluruhnya dari citra Sentinel-2 & Dynamic World "
        "(cloud-masked). Inilah 'leading indicator' yang melengkapi pelaporan "
        "manual SIMPEL."
    )

    # ============ REAL LAND-COVER BEFORE vs AFTER ============
    st.markdown(f"### Komposisi Tutupan Lahan: {yr_base} vs {yr_cur}")

    classes_show = ["Trees", "Built area", "Bare ground", "Shrub & Scrub",
                    "Crops", "Water"]
    rows = []
    for cls in classes_show:
        b = lc_base_get(baseline, cls)
        c = lc_get(baseline, cls)
        if max(b, c) >= 1.0:  # skip negligible classes
            rows.append({"Kelas": cls, "Tahun": str(yr_base), "Persentase": round(b, 1)})
            rows.append({"Kelas": cls, "Tahun": str(yr_cur), "Persentase": round(c, 1)})
    df_ba = pd.DataFrame(rows)

    col_ba, col_kpi = st.columns([2, 1])
    with col_ba:
        fig_ba = px.bar(
            df_ba, x="Kelas", y="Persentase", color="Tahun", barmode="group",
            color_discrete_map={str(yr_base): COLOR_ACCENT, str(yr_cur): COLOR_DANGER},
            text="Persentase",
        )
        fig_ba.update_traces(textposition="outside")
        fig_ba.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10),
                             xaxis_title="", yaxis_title="Persentase Area (%)",
                             legend_title_text="Tahun")
        apply_plot_style(fig_ba)
        st.plotly_chart(fig_ba, use_container_width=True)

    with col_kpi:
        st.markdown("**Perubahan kunci**")
        tree_delta = lc_delta(baseline, "Trees")
        built_delta = lc_delta(baseline, "Built area")
        st.metric(f"Tree Cover {yr_cur}", f"{lc_get(baseline, 'Trees'):.1f}%",
                  fmt_delta_pp(tree_delta, yr_base))
        st.metric(f"Built Area {yr_cur}", f"{lc_get(baseline, 'Built area'):.1f}%",
                  fmt_delta_pp(built_delta, yr_base), delta_color="inverse")
        tl = baseline.get("tree_loss", {})
        if tl.get("loss_2018_2023_ha"):
            st.metric("Hutan hilang 2018–2023 (buffer 1 km)",
                      f"{tl['loss_2018_2023_ha']:.0f} ha")

    # One real satellite context map (Esri current mosaic), honestly labelled.
    st.caption(
        "Peta konteks di bawah memakai Esri World Imagery (mozaik terkini). "
        "Overlay RGB Sentinel-2 before/after live tersedia setelah service account "
        "diberi izin tile Earth Engine (lihat catatan deploy)."
    )
    m_ctx = folium.Map(location=[meta["center_lat"], meta["center_lon"]],
                       zoom_start=12, tiles=None)
    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        attr="Esri World Imagery", name="Satellite (terkini)",
    ).add_to(m_ctx)
    folium.GeoJson(
        geom_geojson,
        style_function=lambda x: {"color": "#FFD700", "weight": 2.5, "fillOpacity": 0.0},
    ).add_to(m_ctx)
    st_folium(m_ctx, height=320, use_container_width=True, returned_objects=[])

    st.markdown("---")

    # ============ NDVI TIMESERIES (real) ============
    st.markdown("### Tren NDVI Tahunan (Sentinel-2)")
    st.caption("NDVI mengukur kerapatan vegetasi (0 = tak bervegetasi, 1 = sangat "
               "rapat). Tahun tanpa citra valid (tertutup awan) dilewati, bukan "
               "ditampilkan sebagai nol.")

    ndvi_series = baseline.get("ndvi", [])
    years = [p["year"] for p in ndvi_series]
    ndvi_values = [p["mean_ndvi"] for p in ndvi_series]  # may contain None

    fig_ndvi = go.Figure()
    fig_ndvi.add_trace(go.Scatter(
        x=years, y=ndvi_values, mode="lines+markers", connectgaps=True,
        line=dict(color=COLOR_PRIMARY, width=3),
        marker=dict(size=12, color=COLOR_ACCENT),
        fill="tozeroy", fillcolor="rgba(46, 117, 182, 0.15)",
    ))
    fig_ndvi.update_layout(
        height=320, margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Tahun", yaxis_title="NDVI (0 sampai 1)",
        yaxis=dict(range=[0, 1]),
        title=f"NDVI Time Series ({years[0]} sampai {years[-1]})" if years else "NDVI",
    )
    apply_plot_style(fig_ndvi)
    st.plotly_chart(fig_ndvi, use_container_width=True)

    # ============ DYNAMIC ALERT from real deltas ============
    st.markdown("---")
    valid = [(p["year"], p["mean_ndvi"]) for p in ndvi_series
             if p.get("mean_ndvi") is not None]
    ndvi_change_pct = None
    if len(valid) >= 2 and valid[0][1]:
        ndvi_change_pct = round((valid[0][1] - valid[-1][1]) / valid[0][1] * 100, 1)
    tree_delta = lc_delta(baseline, "Trees")
    alert = (tree_delta <= -10) or (ndvi_change_pct is not None and ndvi_change_pct >= 20)

    if alert:
        ndvi_line = (f"NDVI turun {ndvi_change_pct}% (dari {valid[0][1]:.2f} di "
                     f"{valid[0][0]} ke {valid[-1][1]:.2f} di {valid[-1][0]}). "
                     if ndvi_change_pct is not None else "")
        st.markdown(f"""
        <div class='alert-box'>
            <h4 style='color: {COLOR_DANGER}; margin-top: 0;'>
                PERUBAHAN TUTUPAN LAHAN TERDETEKSI
            </h4>
            <p><b>Tutupan hutan:</b> {fmt_delta_pp(tree_delta, yr_base)}
            (kini {lc_get(baseline, 'Trees'):.1f}%). {ndvi_line}</p>
            <p><b>Indikasi:</b> konversi tutupan hutan menjadi lahan terbuka / built area.</p>
            <p><b>Rekomendasi:</b> verifikasi lapangan oleh Tim Pengawas Lingkungan
            Hidup (TPLH). Laporan dapat di-export (tab 5) untuk SIMPEL KLHK.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success(
            f"**Tidak ada perubahan signifikan terdeteksi.** Tutupan hutan "
            f"{fmt_delta_pp(tree_delta, yr_base)} (kini {lc_get(baseline, 'Trees'):.1f}%); "
            "NDVI relatif stabil. Area ini terjaga dengan baik."
        )


# ============================================================
# TAB 5: CROSS-CHECK KLAIM AMDAL
# ============================================================
with tab5:
    st.markdown("## Cross-Check Klaim Dokumen AMDAL")
    st.markdown(
        "Fitur ini memverifikasi klaim dalam dokumen AMDAL terhadap data "
        "satelit aktual. Pemrakarsa atau tim penilai KPA dapat memasukkan "
        "pernyataan kunci dari dokumen, dan sistem akan membandingkannya "
        "dengan kondisi lapangan yang terekam citra satelit."
    )

    st.markdown("### Masukkan Klaim dari Dokumen AMDAL")

    preset_claims = {
        "-- Pilih contoh klaim --": "",
        "Klaim 1: Area berupa semak belukar, tidak ada tree cover signifikan.":
            "Area berupa semak belukar, tidak ada tree cover signifikan.",
        "Klaim 2: Tidak ada sungai permanen dalam radius 500 meter.":
            "Tidak ada sungai permanen dalam radius 500 meter.",
        "Klaim 3: Area tidak berada di dekat kawasan lindung.":
            "Area tidak berada di dekat kawasan lindung.",
        "Klaim 4: Topografi relatif datar, tidak ada area curam.":
            "Topografi relatif datar, tidak ada area curam.",
    }

    preset_key = st.selectbox(
        "Contoh klaim (opsional):",
        options=list(preset_claims.keys()),
        index=1,  # default ke klaim 1
    )

    claim = st.text_area(
        "Atau ketik klaim Anda sendiri:",
        value=preset_claims[preset_key],
        height=80,
        placeholder="Contoh: Area proyek berupa lahan bekas kebun yang sudah tidak produktif..."
    )

    col_btn, col_space = st.columns([1, 3])
    with col_btn:
        check_btn = st.button("Jalankan Verifikasi", type="primary", use_container_width=True)

    if check_btn and claim.strip():
        st.markdown("---")
        st.markdown("### Hasil Verifikasi")

        claim_lower = claim.lower()

        findings = []  # list of (severity_label, css_class, finding_text)
        inconsistency_count = 0

        # Real values from the satellite baseline drive every verdict.
        tree_cur = lc_get(baseline, "Trees")
        tree_base = lc_base_get(baseline, "Trees")
        water = baseline.get("water", {})
        near_river = bool(water.get("near_river"))
        nearest_m = water.get("nearest_water_m")
        water_pct = water.get("water_within_polygon_pct", 0) or 0
        prot = baseline.get("protected", {})
        dist_km = prot.get("distance_km")
        overlap = bool(prot.get("overlap"))
        steep = baseline.get("slope", {}).get("steep_pct", 0) or 0
        loss_ha = baseline.get("tree_loss", {}).get("loss_2018_2023_ha")

        # Check 1: "tidak ada tree cover" / "semak belukar"
        if any(kw in claim_lower for kw in ["tidak ada tree", "semak belukar",
                                            "tidak ada hutan", "lahan terbuka"]):
            if max(tree_cur, tree_base) >= 25:
                findings.append(("Inkonsistensi", "critical",
                    f"<strong>INKONSISTEN:</strong> Dynamic World mencatat tree cover "
                    f"<strong>{tree_base:.0f}% pada {yr_base}</strong> dan {tree_cur:.0f}% "
                    f"pada {yr_cur} — jauh di atas definisi 'semak belukar'."))
                if loss_ha:
                    findings.append(("Bukti Tambahan", "critical",
                        f"<strong>Bukti:</strong> Hansen Global Forest Change mencatat "
                        f"<strong>{loss_ha:.0f} ha</strong> hutan hilang 2018–2023 di buffer "
                        "1 km — konsisten dengan tutupan hutan yang signifikan."))
                inconsistency_count += 1
            else:
                findings.append(("Konsisten", "success",
                    f"<strong>KONSISTEN:</strong> tree cover hanya {tree_cur:.0f}% "
                    f"({yr_cur}); klaim area non-hutan wajar."))

        # Check 2: sungai / badan air permanen
        if any(kw in claim_lower for kw in ["tidak ada sungai", "tidak dekat sungai",
                                            "jauh dari sungai"]):
            if near_river or water_pct > 0.5:
                loc = ("DI DALAM polygon" if (nearest_m is not None and nearest_m <= 1)
                       else f"~{nearest_m:.0f} m dari polygon" if nearest_m is not None
                       else "di sekitar polygon")
                findings.append(("Inkonsistensi", "critical",
                    f"<strong>INKONSISTEN:</strong> JRC Global Surface Water mendeteksi "
                    f"badan air permanen (occurrence &gt;75%) {loc}."))
                inconsistency_count += 1
            else:
                findings.append(("Konsisten", "success",
                    "<strong>KONSISTEN:</strong> tidak ada badan air permanen dalam "
                    "radius 2 km dari polygon."))

        # Check 3: kawasan lindung
        if any(kw in claim_lower for kw in ["tidak berada di dekat kawasan lindung",
                                            "jauh dari kawasan lindung",
                                            "tidak dekat kawasan lindung"]):
            if overlap or (dist_km is not None and dist_km < 5):
                d = "beririsan langsung" if overlap else f"hanya {dist_km:.1f} km"
                findings.append(("Inkonsistensi", "critical",
                    f"<strong>INKONSISTEN:</strong> kawasan lindung WDPA {d} dari polygon "
                    "(&lt;5 km dikategorikan 'dekat' per pedoman AMDAL)."))
                inconsistency_count += 1
            else:
                d = "&gt;30 km" if dist_km is None else f"{dist_km:.1f} km"
                findings.append(("Konsisten", "success",
                    f"<strong>KONSISTEN:</strong> kawasan lindung WDPA terdekat {d}, "
                    "dapat dianggap 'tidak dekat'. Catatan: kawasan hutan KLHK belum termasuk."))

        # Check 4: topografi
        if any(kw in claim_lower for kw in ["relatif datar", "tidak ada area curam",
                                            "topografi datar"]):
            if steep >= 10:
                findings.append(("Perlu Klarifikasi", "warning",
                    f"<strong>PERLU KLARIFIKASI:</strong> SRTM DEM menunjukkan {steep:.0f}% "
                    "area memiliki kemiringan &gt;30° (sangat curam per KLHK)."))
                inconsistency_count += 1
            else:
                findings.append(("Konsisten", "success",
                    f"<strong>KONSISTEN:</strong> hanya {steep:.1f}% area curam (&gt;30°); "
                    "topografi memang relatif datar."))

        if not findings:
            findings.append(("Tidak Terklasifikasi", "",
                "Klaim tidak mengandung pernyataan spesifik yang dapat diverifikasi "
                "oleh mesin. Sistem ini mendeteksi klaim tentang tree cover, sungai, "
                "kawasan lindung, dan topografi. Untuk klaim lain, verifikasi manual diperlukan."))

        # Display verdict
        if inconsistency_count >= 2:
            st.error(f"### INKONSISTENSI SIGNIFIKAN TERDETEKSI ({inconsistency_count} temuan)")
        elif inconsistency_count == 1:
            st.warning(f"### INKONSISTENSI TERDETEKSI (1 temuan)")
        else:
            st.success("### KLAIM KONSISTEN DENGAN DATA SATELIT")

        # Display findings
        for severity, css_class, text in findings:
            st.markdown(
                f"<div class='finding-row {css_class}'>"
                f"<span class='finding-label'>{severity}</span>"
                f"{text}"
                "</div>",
                unsafe_allow_html=True,
            )

        # ============ EXPORT: real downloadable report ============
        st.markdown("---")
        st.markdown("### Export Laporan")

        import re as _re
        verdict = ("INKONSISTENSI SIGNIFIKAN" if inconsistency_count >= 2
                   else "INKONSISTENSI TERDETEKSI" if inconsistency_count == 1
                   else "KONSISTEN DENGAN DATA SATELIT")
        plain = [(sev, _re.sub("<[^>]+>", "", txt).replace("&lt;", "<")
                  .replace("&gt;", ">")) for sev, _cls, txt in findings]
        report_md = "\n".join([
            "# Laporan Verifikasi AMDALens",
            f"\n**Area:** {meta.get('name', '-')}  ",
            f"**Centroid:** {meta.get('center_lat')}, {meta.get('center_lon')}  ",
            f"**Luas (satelit):** {area_km2:.1f} km²  " if area_km2 else "",
            f"**Sumber data:** {data_source} | **Dihitung:** {baseline.get('computed_at','-')}",
            f"\n## Skor Risiko Dampak Lingkungan: {total:.0f}/100 — {label}",
            f"Skor tertimbang {result.get('weighted_total','-')}, "
            f"dampak terealisasi {result.get('realized_impact','-')}.",
            "Sub-indeks: " + ", ".join(f"{k} {v:.0f}" for k, v in sub.items()),
            f"\n## Baseline Satelit ({yr_base} → {yr_cur})",
            f"- Tree cover: {tree_base:.0f}% → {tree_cur:.0f}%",
            f"- Built area: {lc_base_get(baseline,'Built area'):.0f}% → "
            f"{lc_get(baseline,'Built area'):.0f}%",
            f"- Area curam (>30°): {steep:.1f}%",
            f"- Badan air dalam polygon: {water_pct:.2f}%; air permanen terdekat: "
            + (f"{nearest_m:.0f} m" if nearest_m is not None else ">2 km"),
            f"- Kawasan lindung WDPA: "
            + ("beririsan" if overlap else f"{dist_km:.1f} km" if dist_km is not None
               else ">30 km"),
            (f"- Hutan hilang 2018–2023 (buffer 1 km): {loss_ha:.0f} ha"
             if loss_ha else ""),
            f"\n## Verifikasi Klaim\n> {claim}\n\n**Hasil:** {verdict} "
            f"({inconsistency_count} temuan inkonsistensi)",
            "\n".join(f"- **{sev}:** {txt}" for sev, txt in plain),
            "\n---\n_AMDALens v0.2 (decision-support, bukan penentu legal). "
            "Sumber: Sentinel-2, Dynamic World, Hansen GFC, SRTM, JRC GSW, WDPA._",
        ])

        col1, col2, col3 = st.columns(3)
        col1.download_button(
            label="⬇ Download laporan (Markdown)",
            data=report_md.encode("utf-8"),
            file_name=f"AMDALens_verifikasi_{demo_key}.md",
            mime="text/markdown",
            use_container_width=True,
        )
        col2.button("Kirim ke Amdalnet (API)", disabled=True, use_container_width=True,
                    help="Integrasi API dengan Amdalnet — roadmap Fase 5")
        col3.button("Publikasikan ke Portal Publik", disabled=True,
                    use_container_width=True,
                    help="Portal transparansi publik — roadmap Fase 5")


# ============ FOOTER ============
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: {COLOR_MUTED}; padding: 1rem; font-size: 0.85rem;'>
    <b>AMDALens v0.2 MVP</b> | Indonesia Aerospace Hackathon 2026<br>
    Data satelit nyata via Google Earth Engine — Sentinel-2, Dynamic World,
    Hansen Global Forest Change, SRTM DEM, JRC Global Surface Water, WDPA.<br>
    <i>Open data, open science, open government.</i>
</div>
""", unsafe_allow_html=True)
