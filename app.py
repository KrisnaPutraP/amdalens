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
    COLOR_MUTED, COLOR_SOFT, WEIGHTS, DW_CLASSES, DW_COLORS,
    BASELINE_YEAR, CURRENT_YEAR, DISCLAIMER,
)
from sample_polygons import get_demo_polygon, MOROWALI_META, REFERENCE_FOREST_META
from risk_engine import (
    compute_total_score, driver_narrative,
    mock_score_morowali, mock_score_reference,
    score_ipth, score_ikh, score_isr, score_ikkl, score_isb,
)

# ============ UI THEME ============
TEXT_COLOR = "#17202A"
MUTED_TEXT = "#5C6675"
PAGE_BG = "#F5F7FA"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F1F6FA"
BORDER = "#D7E0EA"
SHADOW = "0 10px 26px rgba(31, 78, 121, 0.08)"


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


# ============ PAGE CONFIG ============
st.set_page_config(
    page_title=f"{APP_TITLE} - AMDAL Intelligence Layer",
    page_icon="A",
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

    [data-testid="stToolbar"] {{
        background: rgba(255, 255, 255, 0.98) !important;
        color: var(--amdalens-text) !important;
        right: 0.75rem !important;
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

    .brand-mark {{
        align-items: center;
        background: linear-gradient(135deg, #0B4F6C 0%, #2E75B6 100%);
        border: 1px solid #94B8D8;
        border-radius: 8px;
        box-shadow: var(--amdalens-shadow);
        color: #FFFFFF;
        display: flex;
        font-size: 1.25rem;
        font-weight: 800;
        height: 4.2rem;
        justify-content: center;
        letter-spacing: 0;
        margin: 0.1rem auto 0;
        width: 4.2rem;
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
@st.cache_resource
def init_gee():
    """Initialize Earth Engine. Falls back to mock mode if unavailable."""
    try:
        import ee
        local_secrets = Path.cwd() / ".streamlit" / "secrets.toml"
        user_secrets = Path.home() / ".streamlit" / "secrets.toml"
        has_secrets_file = local_secrets.exists() or user_secrets.exists()

        # Try credential from st.secrets first
        if has_secrets_file and "gee_service_account" in st.secrets:
            import json
            sa_info = dict(st.secrets["gee_service_account"])
            credentials = ee.ServiceAccountCredentials(
                email=sa_info["client_email"],
                key_data=json.dumps(sa_info)
            )
            ee.Initialize(credentials, project=sa_info.get("project_id"))
        else:
            # Try local authentication
            project_id = st.secrets.get("gee_project_id", None) if has_secrets_file else None
            ee.Initialize(project=project_id)
        return True, None
    except Exception as e:
        return False, str(e)


# ============ HEADER ============
col_logo, col_title = st.columns([1, 6])
with col_logo:
    st.markdown("<div class='brand-mark'>AL</div>", unsafe_allow_html=True)
with col_title:
    st.markdown(f"<div class='main-title'>{APP_TITLE}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='subtitle'>{APP_SUBTITLE}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='tagline'>{APP_TAGLINE}</div>", unsafe_allow_html=True)

st.markdown("---")


# ============ SIDEBAR ============
with st.sidebar:
    st.markdown("### Pilih Area Analisis")

    polygon_choice = st.radio(
        "Polygon Demo",
        options=["Morowali (Demo KRITIS)", "Reference Area (Demo AMAN)", "Upload Sendiri"],
        index=0,
        help="Untuk hackathon, gunakan polygon dummy. Upload file akan tersedia di versi berikutnya."
    )

    st.markdown("---")
    st.markdown("### Mode Komputasi")

    use_live_gee = st.checkbox(
        "Gunakan Google Earth Engine (live)",
        value=False,
        help="Aktifkan untuk query GEE sungguhan. Perlu authentikasi service account."
    )

    if use_live_gee:
        if "gee_ready" not in st.session_state:
            ok, err = init_gee()
            st.session_state.gee_ready = ok
            st.session_state.gee_error = err

        if not st.session_state.gee_ready:
            st.error(f"GEE tidak tersedia: {st.session_state.gee_error}")
            st.info("Jalankan di mode demo (precomputed) untuk sekarang.")
            use_live_gee = False

    st.session_state.use_live_gee = use_live_gee

    if not use_live_gee:
        st.info("**Mode Demo:** menggunakan hasil precomputed untuk kecepatan rekaman video.")

    st.markdown("---")
    st.markdown("### Bobot Skor Risiko")
    with st.expander("Lihat formula", expanded=True):
        st.markdown(
            """
            <div class="formula-box">
                <div class="formula-title">Skor Risiko = jumlah kontribusi tertimbang</div>
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

    st.markdown("---")
    st.caption("Indonesia Aerospace Hackathon 2026")
    st.caption("Proposal: AMDALens v0.1 MVP")


# ============ POLYGON SELECTION ============
if "Morowali" in polygon_choice:
    geom_geojson, meta = get_demo_polygon("morowali")
    demo_key = "morowali"
elif "Reference" in polygon_choice:
    geom_geojson, meta = get_demo_polygon("reference")
    demo_key = "reference"
else:
    st.warning("Upload polygon akan tersedia di versi berikutnya. Silakan pilih polygon demo di sidebar.")
    geom_geojson, meta = get_demo_polygon("morowali")
    demo_key = "morowali"


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
        "Langkah pertama: pemrakarsa mengunggah polygon lokasi proyek "
        "(IUP, HGU, IPPKH, atau KLHS). Untuk demo ini, kami gunakan polygon "
        "ilustratif di area yang telah terdokumentasi publik."
    )

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
            style_function=lambda x: {
                "color": COLOR_DANGER if demo_key == "morowali" else COLOR_SUCCESS,
                "weight": 3,
                "fillColor": COLOR_DANGER if demo_key == "morowali" else COLOR_SUCCESS,
                "fillOpacity": 0.2,
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
        st.markdown(f"**Luas Estimasi:** {meta['approx_area_km2']} km²")
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

    # ============ LAND COVER CLASSIFICATION (Dynamic World) ============
    st.markdown("### Klasifikasi Tutupan Lahan (Dynamic World, 10 m)")

    # Mock data for demo (based on Morowali context: mixed but changed area)
    if demo_key == "morowali":
        lc_data = {
            "Trees": 38.5,
            "Shrub & Scrub": 22.3,
            "Bare ground": 18.7,
            "Built area": 9.8,
            "Crops": 5.2,
            "Grass": 3.5,
            "Water": 1.5,
            "Flooded vegetation": 0.5,
        }
    else:  # reference forest
        lc_data = {
            "Trees": 89.2,
            "Shrub & Scrub": 6.8,
            "Grass": 2.1,
            "Water": 1.3,
            "Flooded vegetation": 0.4,
            "Bare ground": 0.2,
        }

    col_chart, col_stats = st.columns([2, 1])
    with col_chart:
        df_lc = pd.DataFrame({
            "Kelas": list(lc_data.keys()),
            "Persentase": list(lc_data.values()),
        })
        # Color map matching DW classes
        class_color_map = {
            "Water": "#419BDF", "Trees": "#397D49", "Grass": "#88B053",
            "Flooded vegetation": "#7A87C6", "Crops": "#E49635",
            "Shrub & Scrub": "#DFC35A", "Built area": "#C4281B",
            "Bare ground": "#A59B8F",
        }
        fig = px.bar(
            df_lc, x="Persentase", y="Kelas", orientation="h",
            color="Kelas", color_discrete_map=class_color_map,
            text=df_lc["Persentase"].apply(lambda x: f"{x}%"),
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
        st.markdown("**Ringkasan**")
        if demo_key == "morowali":
            st.metric("Tree Cover", f"{lc_data['Trees']}%", "-12% vs 2019", delta_color="inverse")
            st.metric("Built Area", f"{lc_data['Built area']}%", "+7% vs 2019")
            st.metric("Bare Ground", f"{lc_data['Bare ground']}%", "+11% vs 2019", delta_color="inverse")
        else:
            st.metric("Tree Cover", f"{lc_data['Trees']}%", "stabil vs 2019")
            st.metric("Water", f"{lc_data['Water']}%")
            st.metric("Bare Ground", f"{lc_data['Bare ground']}%", "stabil")

    st.caption("Sumber: Google/WRI Dynamic World V1 (klasifikasi 10 m, near real-time)")

    st.markdown("---")

    # ============ TOPOGRAPHY (SRTM) ============
    st.markdown("### Topografi dan Kemiringan Lereng (SRTM DEM 30 m)")

    if demo_key == "morowali":
        slope_mean, slope_max, steep_pct = 18.3, 52.7, 22.1
    else:
        slope_mean, slope_max, steep_pct = 25.1, 48.0, 29.5

    c1, c2, c3 = st.columns(3)
    c1.metric("Kemiringan Rata-rata", f"{slope_mean}°")
    c2.metric("Kemiringan Maksimum", f"{slope_max}°")
    c3.metric("Area Curam (>30°)", f"{steep_pct}%",
              help="Per Pedoman KLHK, kemiringan >30° masuk kategori sangat curam")

    st.caption("Sumber: NASA SRTM DEM v4 (30 m global elevation)")

    st.markdown("---")

    # ============ HIDROLOGI ============
    st.markdown("### Analisis Hidrologi (JRC Global Surface Water)")

    if demo_key == "morowali":
        water_pct, near_river = 0.8, True
        river_note = "Polygon berbatasan dengan sungai permanen (jarak <500 m dari tepi)"
    else:
        water_pct, near_river = 1.3, False
        river_note = "Terdapat sungai kecil dalam polygon, tidak ada aliran utama"

    c1, c2 = st.columns(2)
    c1.metric("Badan Air Permanen dalam Polygon", f"{water_pct}%")
    c2.metric("Kedekatan Sungai Utama", "Dekat" if near_river else "Tidak dekat",
              delta="HIGH RISK" if near_river else None,
              delta_color="inverse" if near_river else "off")
    st.caption(f"Catatan: {river_note}")
    st.caption("Sumber: European Commission JRC Global Surface Water (30 m, 1984 hingga sekarang)")

    st.markdown("---")

    # ============ KEDEKATAN KAWASAN LINDUNG ============
    st.markdown("### Kedekatan ke Kawasan Lindung")

    if demo_key == "morowali":
        dist_km, overlap = 3.2, False
    else:
        dist_km, overlap = 8.5, False

    c1, c2 = st.columns(2)
    c1.metric("Jarak ke Kawasan Lindung Terdekat", f"{dist_km} km",
              delta="<5 km" if dist_km < 5 else ">5 km",
              delta_color="inverse" if dist_km < 5 else "off")
    c2.metric("Overlap dengan Kawasan Lindung", "Ya" if overlap else "Tidak",
              delta="KRITIS" if overlap else "Aman",
              delta_color="inverse" if overlap else "normal")
    st.caption("Sumber: WDPA Protected Planet + KLHK Kawasan Hutan")


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

    # Compute scores
    if demo_key == "morowali":
        result = mock_score_morowali()
    else:
        result = mock_score_reference()

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
        "Perbandingan kondisi tutupan lahan antara tahun baseline "
        f"({BASELINE_YEAR}) dan tahun terkini ({CURRENT_YEAR}). Sistem "
        "memproses citra Sentinel-2 secara near real-time (revisit 5 hari), "
        "dengan cloud-masking untuk memastikan akurasi."
    )

    # Before-after side-by-side
    st.markdown(f"### Citra Satelit: {BASELINE_YEAR} vs {CURRENT_YEAR}")

    col_before, col_after = st.columns(2)

    with col_before:
        st.markdown(f"#### Baseline ({BASELINE_YEAR})")
        # Use Esri imagery via Folium as proxy for S2 composite
        m_before = folium.Map(
            location=[meta["center_lat"], meta["center_lon"]],
            zoom_start=12, tiles=None,
        )
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri", name="Satellite",
        ).add_to(m_before)
        folium.GeoJson(
            geom_geojson,
            style_function=lambda x: {"color": "#FFD700", "weight": 2.5, "fillOpacity": 0.0},
        ).add_to(m_before)
        folium.Marker(
            [meta["center_lat"], meta["center_lon"]],
            tooltip=f"{BASELINE_YEAR}: Baseline",
            icon=folium.Icon(color="green", icon="leaf"),
        ).add_to(m_before)
        st_folium(m_before, height=350, use_container_width=True, returned_objects=[])
        if demo_key == "morowali":
            st.info(f"**Tree Cover {BASELINE_YEAR}:** 50.8% | Area terbuka masih minimal")
        else:
            st.info(f"**Tree Cover {BASELINE_YEAR}:** 90.1% | Hutan intact")

    with col_after:
        st.markdown(f"#### Kondisi Saat Ini ({CURRENT_YEAR})")
        m_after = folium.Map(
            location=[meta["center_lat"], meta["center_lon"]],
            zoom_start=12, tiles=None,
        )
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri", name="Satellite",
        ).add_to(m_after)
        folium.GeoJson(
            geom_geojson,
            style_function=lambda x: {"color": "#FF2020", "weight": 2.5, "fillOpacity": 0.0},
        ).add_to(m_after)
        folium.Marker(
            [meta["center_lat"], meta["center_lon"]],
            tooltip=f"{CURRENT_YEAR}: Current",
            icon=folium.Icon(color="red", icon="warning-sign"),
        ).add_to(m_after)
        st_folium(m_after, height=350, use_container_width=True, returned_objects=[])
        if demo_key == "morowali":
            st.error(f"**Tree Cover {CURRENT_YEAR}:** 38.5% | **Penurunan 12.3 poin dalam 6 tahun**")
        else:
            st.success(f"**Tree Cover {CURRENT_YEAR}:** 89.2% | **Stabil (-0.9 poin)**")

    st.markdown("---")

    # ============ NDVI TIMESERIES ============
    st.markdown("### Tren NDVI Tahunan")
    st.caption("NDVI (Normalized Difference Vegetation Index) mengukur kerapatan vegetasi. "
               "Nilai 0 menunjukkan lahan tidak bervegetasi, nilai 1 menunjukkan vegetasi sangat rapat.")

    years = list(range(2019, 2026))
    if demo_key == "morowali":
        ndvi_values = [0.72, 0.69, 0.64, 0.58, 0.53, 0.49, 0.47]
    else:
        ndvi_values = [0.82, 0.83, 0.81, 0.82, 0.80, 0.81, 0.82]

    df_ndvi = pd.DataFrame({"Tahun": years, "NDVI Rata-rata": ndvi_values})

    fig_ndvi = go.Figure()
    fig_ndvi.add_trace(go.Scatter(
        x=df_ndvi["Tahun"], y=df_ndvi["NDVI Rata-rata"],
        mode="lines+markers", line=dict(color=COLOR_PRIMARY, width=3),
        marker=dict(size=12, color=COLOR_ACCENT),
        fill="tozeroy", fillcolor="rgba(46, 117, 182, 0.15)",
    ))
    fig_ndvi.update_layout(
        height=320, margin=dict(l=10, r=10, t=30, b=10),
        xaxis_title="Tahun", yaxis_title="NDVI (0 sampai 1)",
        yaxis=dict(range=[0, 1]),
        title=f"NDVI Time Series ({years[0]} sampai {years[-1]})",
    )
    apply_plot_style(fig_ndvi)
    st.plotly_chart(fig_ndvi, use_container_width=True)

    # ============ ALERT BOX ============
    st.markdown("---")
    if demo_key == "morowali":
        change_pct = round((ndvi_values[0] - ndvi_values[-1]) / ndvi_values[0] * 100, 1)
        st.markdown(f"""
        <div class='alert-box'>
            <h4 style='color: {COLOR_DANGER}; margin-top: 0;'>
                POTENTIAL LAND COVER CHANGE DETECTED
            </h4>
            <p><b>Perubahan NDVI:</b> Rata-rata NDVI menurun dari {ndvi_values[0]:.2f} 
            ({years[0]}) menjadi {ndvi_values[-1]:.2f} ({years[-1]}), penurunan sebesar 
            <b>{change_pct}%</b>.</p>
            <p><b>Indikasi:</b> Pola penurunan konsisten selama 6 tahun mengindikasikan 
            konversi tutupan hutan menjadi lahan terbuka atau built area.</p>
            <p><b>Rekomendasi:</b> Sistem merekomendasikan verifikasi lapangan oleh 
            Tim Pengawas Lingkungan Hidup (TPLH). Laporan dapat di-export untuk 
            diintegrasikan dengan SIMPEL KLHK.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success("""
        **Tidak ada perubahan signifikan terdeteksi.** NDVI rata-rata stabil 
        pada kisaran 0.80 sampai 0.83 selama 6 tahun observasi. Tutupan hutan 
        di area ini terjaga dengan baik.
        """)


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

        # Check 1: "tidak ada tree cover" / "semak belukar"
        if any(kw in claim_lower for kw in ["tidak ada tree", "semak belukar", "tidak ada hutan", "lahan terbuka"]):
            if demo_key == "morowali":
                findings.append(("Inkonsistensi", "critical",
                    "<strong>INKONSISTEN:</strong> Data Dynamic World pada baseline 2019 menunjukkan "
                    "<strong>50.8% area terklasifikasi sebagai Tree Cover</strong>, jauh di atas definisi "
                    "'semak belukar'. Pada 2025, tree cover turun menjadi 38.5% (masih signifikan)."))
                findings.append(("Bukti Tambahan", "critical",
                    "<strong>Bukti tambahan:</strong> Hansen Global Forest Change mencatat area ini memiliki "
                    "canopy density >30% pada baseline 2000, konsisten dengan klasifikasi sebagai hutan sekunder."))
                inconsistency_count += 2
            else:
                findings.append(("Inkonsistensi", "critical",
                    "<strong>INKONSISTEN:</strong> Data Dynamic World menunjukkan 89.2% area adalah "
                    "Tree Cover (hutan primer/sekunder), bukan semak belukar."))
                inconsistency_count += 1

        # Check 2: sungai permanen
        if any(kw in claim_lower for kw in ["tidak ada sungai", "tidak dekat sungai", "jauh dari sungai"]):
            if demo_key == "morowali":
                findings.append(("Inkonsistensi", "critical",
                    "<strong>INKONSISTEN:</strong> JRC Global Surface Water menunjukkan badan air permanen "
                    "(occurrence >75%) berada dalam jarak &lt;500 m dari batas polygon. Klaim "
                    "'tidak ada sungai permanen' tidak sesuai data satelit."))
                inconsistency_count += 1
            else:
                findings.append(("Sebagian Konsisten", "warning",
                    "<strong>SEBAGIAN KONSISTEN:</strong> Terdapat aliran air kecil namun bukan sungai utama "
                    "dalam radius yang disebutkan."))

        # Check 3: kawasan lindung
        if any(kw in claim_lower for kw in ["tidak berada di dekat kawasan lindung", "jauh dari kawasan lindung"]):
            if demo_key == "morowali":
                findings.append(("Inkonsistensi", "critical",
                    "<strong>INKONSISTEN:</strong> Kawasan lindung terdekat berada pada jarak 3.2 km. "
                    "Dalam konteks pedoman AMDAL, jarak &lt;5 km umumnya dikategorikan 'dekat'."))
                inconsistency_count += 1
            else:
                findings.append(("Konsisten", "success",
                    "<strong>KONSISTEN:</strong> Kawasan lindung terdekat berada 8.5 km, dapat dianggap 'tidak dekat'."))

        # Check 4: topografi
        if any(kw in claim_lower for kw in ["relatif datar", "tidak ada area curam", "topografi datar"]):
            if demo_key == "morowali":
                findings.append(("Perlu Klarifikasi", "warning",
                    "<strong>PERLU KLARIFIKASI:</strong> SRTM DEM menunjukkan 22.1% area memiliki kemiringan "
                    ">30° (sangat curam per KLHK). Klaim 'tidak ada area curam' tidak akurat, "
                    "meskipun kemiringan rata-rata memang moderat (18.3°)."))
                inconsistency_count += 1

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

        # Export option
        st.markdown("---")
        st.markdown("### Export Laporan")
        col1, col2, col3 = st.columns(3)
        col1.download_button(
            label="Download laporan verifikasi (PDF)",
            data="(Demo: laporan PDF akan digenerate di versi produksi)",
            file_name="AMDALens_verification_report.pdf",
            disabled=True,
            help="Akan aktif di versi v0.2",
        )
        col2.button("Kirim ke Amdalnet (API)", disabled=True,
                    help="Integrasi API dengan Amdalnet direncanakan di Fase 5 roadmap")
        col3.button("Publikasikan ke Portal Publik", disabled=True,
                    help="Opsional untuk transparansi publik")


# ============ FOOTER ============
st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: {COLOR_MUTED}; padding: 1rem; font-size: 0.85rem;'>
    <b>AMDALens v0.1 MVP</b> | Indonesia Aerospace Hackathon 2026<br>
    Dibangun dengan Google Earth Engine, Streamlit, Sentinel-2, Dynamic World, 
    Hansen Global Forest Change, SRTM DEM, dan JRC Global Surface Water.<br>
    <i>Open data, open science, open government.</i>
</div>
""", unsafe_allow_html=True)
