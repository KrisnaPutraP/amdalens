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

# Alternatif: polygon kecil di area yang lebih terjaga (untuk perbandingan low-risk)
REFERENCE_FOREST_POLYGON = {
    "type": "Polygon",
    "coordinates": [[
        [121.480, -1.880],
        [121.510, -1.880],
        [121.510, -1.910],
        [121.480, -1.910],
        [121.480, -1.880],
    ]]
}

REFERENCE_FOREST_META = {
    "name": "Reference Polygon - Forest Area",
    "province": "Sulawesi Tengah",
    "district": "Kabupaten Morowali Utara",
    "subdistrict": "(area hutan referensi)",
    "proj_type_hypothesis": "Area hutan (kontrol / benchmark low-risk)",
    "center_lat": -1.895,
    "center_lon": 121.495,
    "approx_area_km2": 10.0,
    "note": "Digunakan sebagai pembanding: polygon di area yang masih berupa hutan."
}


def get_demo_polygon(key: str = "morowali"):
    """Return (geojson_geometry, metadata_dict) for a demo polygon."""
    if key == "morowali":
        return MOROWALI_DEMO_POLYGON, MOROWALI_META
    elif key == "reference":
        return REFERENCE_FOREST_POLYGON, REFERENCE_FOREST_META
    else:
        raise ValueError(f"Unknown demo polygon key: {key}")