# AMDALens MVP

Platform Intelijen Verifikasi AMDAL Berbasis Satelit. Demo untuk Indonesia Aerospace Hackathon 2026.

## Fitur MVP

1. **Upload / Pilih Polygon Proyek** (tab 1) — polygon demo Morowali dan area referensi hutan.
2. **Auto-Baseline** (tab 2) — klasifikasi tutupan lahan Dynamic World, slope SRTM, hidrologi JRC, kedekatan kawasan lindung.
3. **Environmental Risk Score** (tab 3) — skor 0 sampai 100 dengan breakdown 5 sub-indeks (IPTH, IKH, ISR, IKKL, ISB).
4. **Compliance Monitoring** (tab 4) — before/after Sentinel-2, tren NDVI 2019 sampai 2025, alert perubahan.
5. **Cross-Check Klaim AMDAL** (tab 5) — verifikasi klaim dokumen terhadap data satelit.

## Quick Start (Demo Mode, tanpa GEE)

```bash
cd amdalens_mvp
python -m venv venv
source venv/bin/activate    # Linux/Mac
# atau: venv\Scripts\activate   # Windows

pip install -r requirements.txt

streamlit run app.py
```

App akan terbuka di `http://localhost:8501`. Mode demo menggunakan data precomputed, jadi tidak memerlukan setup Google Earth Engine. Cocok untuk rekam video demo.

## Setup Penuh dengan Google Earth Engine (opsional)

Mode GEE live memerlukan autentikasi. Dua cara:

### Cara 1 — Authenticate Lokal (Paling Cepat)

```bash
earthengine authenticate
```

Lalu di app, centang "Gunakan Google Earth Engine (live)" di sidebar.

### Cara 2 — Service Account untuk Deploy ke Streamlit Cloud

1. Buat Google Cloud project di https://console.cloud.google.com.
2. Enable Earth Engine API di project tersebut.
3. Daftar project ke Earth Engine di https://code.earthengine.google.com/register.
4. Buat Service Account: IAM & Admin → Service Accounts → Create.
5. Tambahkan role "Earth Engine Resource Viewer".
6. Download JSON key.
7. Di Streamlit Cloud, masuk ke Settings → Secrets, tambahkan:

```toml
[gee_service_account]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "amdalens-sa@your-project-id.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
```

## Deploy ke Streamlit Community Cloud (gratis)

1. Push kode ke GitHub repo.
2. Buka https://share.streamlit.io/.
3. Connect repo, pilih `app.py` sebagai main file.
4. Tambahkan secrets di settings (lihat di atas).
5. Deploy. URL akan seperti `https://amdalens.streamlit.app`.

## Struktur File

```
amdalens_mvp/
├── app.py                # Streamlit dashboard (UI utama)
├── config.py             # Konstanta, styling, konfigurasi GEE
├── risk_engine.py        # Formula Skor Risiko 5 sub-indeks
├── gee_pipeline.py       # Semua fungsi Google Earth Engine
├── sample_polygons.py    # Polygon demo Morowali dan referensi
├── requirements.txt      # Dependencies Python
├── README.md             # File ini
└── DEMO_SCRIPT.md        # Skrip narasi video demo
```

## Catatan Teknis

- **Mode demo vs mode live**: Mode demo menggunakan angka precomputed di `app.py` untuk kecepatan dan reliabilitas saat merekam video. Mode live memanggil `gee_pipeline.py` untuk query nyata ke GEE. Untuk hackathon, mode demo direkomendasikan agar video tidak terganggu latency GEE.

- **Cloud cover**: Sentinel-2 di daerah tropis sering tertutup awan. Pipeline menerapkan `CLOUDY_PIXEL_PERCENTAGE < 20%` filter dan QA60 masking. Di atas ekuator, median composite tahunan biasanya cukup bersih.

- **Rate limit GEE**: Tier gratis memiliki kuota. Untuk demo hackathon cukup, tetapi untuk produksi perlu upgrade ke commercial tier atau cache hasil di database lokal.

## Troubleshooting

**Error "Earth Engine client library not installed"**  
```bash
pip install earthengine-api
```

**Error "Project is not registered for Earth Engine"**  
Daftarkan project di https://code.earthengine.google.com/register.

**Map tidak muncul**  
Cek koneksi internet. Folium membutuhkan tile server (Esri, OSM).

**Streamlit hang saat load GEE**  
Matikan mode live, pakai mode demo. GEE query pertama bisa lama karena server Google harus "warm up" tile cache.

## Lisensi

MIT License (untuk kode hackathon). Dataset yang digunakan memiliki lisensi masing-masing, lihat sumber di tab GEE Data Catalog.