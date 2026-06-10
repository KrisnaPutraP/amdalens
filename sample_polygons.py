"""
AMDALens - Sample Polygons
Polygon dummy untuk demo. Fokus pada Kecamatan Bahodopi, Kabupaten Morowali,
Sulawesi Tengah. Area ini dipilih karena telah terdokumentasi secara publik
mengalami ekspansi aktivitas pertambangan nikel dalam dekade terakhir, sehingga
analisis satelit dapat divalidasi silang dengan data publik ESDM/KLHK.

Koordinat adalah aproksimasi untuk demo. Polygon bersifat ilustratif dan
tidak mewakili batas konsesi resmi perusahaan manapun.
"""

# Polygon demo Morowali (Kec. Bahodopi, Sulawesi Tengah)
# Koordinat dalam format [lon, lat] (EPSG:4326)
# Area kira-kira 25-35 km^2, cocok untuk demo hackathon
MOROWALI_DEMO_POLYGON = {
    "type": "Polygon",
    "coordinates": [[
        [122.135, -2.805],
        [122.175, -2.805],
        [122.185, -2.835],
        [122.175, -2.870],
        [122.135, -2.875],
        [122.115, -2.850],
        [122.120, -2.820],
        [122.135, -2.805],
    ]]
}

MOROWALI_META = {
    "name": "Demo Polygon - Bahodopi, Morowali",
    "province": "Sulawesi Tengah",
    "district": "Kabupaten Morowali",
    "subdistrict": "Kecamatan Bahodopi",
    "proj_type_hypothesis": "Pertambangan Nikel (ilustrasi)",
    "center_lat": -2.840,
    "center_lon": 122.150,
    "approx_area_km2": 30.0,
    "note": (
        "Polygon ilustratif untuk demo hackathon. Tidak mewakili konsesi "
        "perusahaan tertentu. Lokasi dipilih karena tutupan lahan di sekitar "
        "area telah terdokumentasi publik mengalami perubahan signifikan "
        "sejak 2015-2020."
    )
}

# Polygon pembanding low-risk: hutan stabil ~8 km di barat kawasan industri IMIP,
# masih di Kec. Bahodopi. Kontras "satu kecamatan, dua nasib": inti industri
# (KRITIS) vs hutan tetangga yang masih utuh (AMAN). Tutupan hutan stabil, datar,
# jauh dari air permanen & kawasan lindung formal -> benchmark risiko rendah.
REFERENCE_FOREST_POLYGON = {
    "type": "Polygon",
    "coordinates": [[
        [122.062, -2.826],
        [122.090, -2.828],
        [122.094, -2.848],
        [122.072, -2.858],
        [122.058, -2.846],
        [122.062, -2.826],
    ]]
}

REFERENCE_FOREST_META = {
    "name": "Reference - Hutan Stabil Bahodopi Barat",
    "province": "Sulawesi Tengah",
    "district": "Kabupaten Morowali",
    "subdistrict": "Kecamatan Bahodopi (barat)",
    "proj_type_hypothesis": "Hutan stabil (benchmark risiko rendah)",
    "center_lat": -2.842,
    "center_lon": 122.076,
    "approx_area_km2": 8.0,
    "note": (
        "Pembanding low-risk: hutan yang masih utuh ~8 km di barat kawasan "
        "industri nikel IMIP, masih dalam Kec. Bahodopi. Tutupan hutan stabil "
        "2019-2025, topografi relatif datar, jauh dari air permanen dan kawasan "
        "lindung formal. Menunjukkan skor risiko AMDALens memang membedakan "
        "area aman dari area kritis, bukan selalu menilai tinggi."
    )
}


def get_demo_polygon(key: str = "morowali"):
    """Return (geojson_geometry, metadata_dict) for a demo polygon."""
    if key == "morowali":
        return MOROWALI_DEMO_POLYGON, MOROWALI_META
    elif key == "reference":
        return REFERENCE_FOREST_POLYGON, REFERENCE_FOREST_META
    else:
        raise ValueError(f"Unknown demo polygon key: {key}")