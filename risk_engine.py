"""
AMDALens - Risk Scoring Engine

Implementasi formula Skor Risiko Dampak Lingkungan (0-100) sesuai proposal:

    Skor = 0.30 * IPTH + 0.25 * IKH + 0.20 * ISR + 0.15 * IKKL + 0.10 * ISB

Setiap sub-indeks dinormalisasi ke rentang 0-100 sebelum dibobotkan.
"""
from config import WEIGHTS, classify_risk


def score_ipth(annual_loss_pct: float) -> float:
    """
    IPTH: Indeks Perubahan Tutupan Hutan (buffer 1 km, 5 tahun terakhir).
    Polygon dengan loss >15%/tahun mendapat 100, tanpa loss mendapat 0.
    Scaling linear antara keduanya.
    """
    if annual_loss_pct <= 0:
        return 0.0
    if annual_loss_pct >= 15:
        return 100.0
    return (annual_loss_pct / 15.0) * 100


def score_ikh(water_within_pct: float, nearest_water_m: float = None,
              near_river_flag: bool = False) -> float:
    """
    IKH: Indeks Kerentanan Hidrologi.
    Gabungan dua sinyal nyata dari JRC Global Surface Water:
      (a) badan air permanen DI DALAM polygon -> paparan banjir/limpasan langsung
      (b) kedekatan ke air permanen / sungai / pesisir terdekat (meter)
    Versi produksi menambah layer sungai OSM dan zona rawan banjir BNPB.
    """
    inside = min((water_within_pct or 0) * 8.0, 50.0)   # 6.25% air -> 50
    if nearest_water_m is None:
        prox = 25.0 if near_river_flag else 0.0
    elif nearest_water_m <= 100:
        prox = 50.0
    elif nearest_water_m <= 500:
        prox = 35.0
    elif nearest_water_m <= 1500:
        prox = 15.0
    else:
        prox = 0.0
    return round(min(inside + prox, 100.0), 1)


def score_isr(steep_pct: float) -> float:
    """
    ISR: Indeks Slope Risk.
    Persentase area dengan kemiringan >30 derajat.
    Polygon dengan >40% area curam mendapat 100.
    """
    if steep_pct <= 0:
        return 0.0
    if steep_pct >= 40:
        return 100.0
    return (steep_pct / 40.0) * 100


def score_ikkl(distance_to_protected_km: float = None,
               overlap_with_protected: bool = False) -> float:
    """
    IKKL: Indeks Kedekatan Kawasan Lindung.
    - Beririsan langsung dengan kawasan lindung = 100
    - Distance-decay linear: <1 km = 80, 1-5 km = 60-80, 5-10 km = 20-60, >10 km = 0.

    Untuk MVP: pakai proxy sederhana. Versi produksi pakai WDPA/KLHK layer.
    """
    if overlap_with_protected:
        return 100.0
    if distance_to_protected_km is None:
        return 50.0  # default medium risk kalau data tidak tersedia
    if distance_to_protected_km <= 1:
        return 80.0
    if distance_to_protected_km <= 5:
        return 60.0 + (5 - distance_to_protected_km) * 5
    if distance_to_protected_km <= 10:
        return 20.0 + (10 - distance_to_protected_km) * 8
    return 0.0


def score_isb(biodiversity_overlap_pct: float = None,
              regional_prior: float = 55.0) -> float:
    """
    ISB: Indeks Sensitivitas Biodiversitas.
    Overlap polygon dengan habitat spesies terancam (IUCN) atau KBA.
    Untuk MVP: jika overlap belum dihitung, pakai prior regional (mis. Wallacea
    = tinggi). Versi produksi memakai layer IUCN Red List dan KBA penuh.
    """
    if biodiversity_overlap_pct is not None:
        return min(biodiversity_overlap_pct * 2, 100)  # 50% overlap = 100
    return float(regional_prior)


def compute_total_score(sub_indices: dict) -> dict:
    """
    Hitung skor agregat dari dict sub-indeks.

    Input:
        {"IPTH": float, "IKH": float, "ISR": float, "IKKL": float, "ISB": float}

    Output:
        {
            "total": float,
            "label": str,
            "color": str,
            "status_text": str,
            "weighted_contributions": {code: weighted_value},
            "sub_indices": {code: raw_value}
        }
    """
    total = 0.0
    contributions = {}
    for code, weight in WEIGHTS.items():
        val = sub_indices.get(code, 0)
        contribution = val * weight
        contributions[code] = round(contribution, 2)
        total += contribution

    total = round(total, 1)
    label, color, status_text = classify_risk(total)

    return {
        "total": total,
        "label": label,
        "color": color,
        "status_text": status_text,
        "weighted_contributions": contributions,
        "sub_indices": sub_indices,
    }


def driver_narrative(result: dict) -> str:
    """Generate plain-language explanation of top risk drivers."""
    contribs = result["weighted_contributions"]
    # Sort by weighted contribution
    sorted_c = sorted(contribs.items(), key=lambda x: x[1], reverse=True)
    top_code, top_val = sorted_c[0]
    second_code, second_val = sorted_c[1]

    names = {
        "IPTH": "Perubahan Tutupan Hutan",
        "IKH": "Kerentanan Hidrologi",
        "ISR": "Slope Risk",
        "IKKL": "Kedekatan Kawasan Lindung",
        "ISB": "Sensitivitas Biodiversitas",
    }

    return (
        f"Driver utama risiko adalah **{names[top_code]}** "
        f"(kontribusi tertimbang: {top_val:.1f} poin), "
        f"diikuti oleh **{names[second_code]}** ({second_val:.1f} poin)."
    )


# ============ IPTH v2: gabung laju-loss + tingkat konversi ============
def converted_pct(landcover: dict) -> float:
    """% lahan terkonversi/terbuka (Built area + Bare ground) dari klasifikasi DW."""
    return float((landcover or {}).get("Built area", 0)
                 + (landcover or {}).get("Bare ground", 0))


def score_ipth_v2(annual_loss_pct: float, converted_land_pct: float) -> float:
    """
    IPTH (Indeks Perubahan Tutupan Hutan) versi terkalibrasi.

    Mengukur degradasi tutupan hutan dari DUA sisi, lalu diambil maksimum:
      - laju kehilangan terbaru (Hansen/NDVI): 15%/th -> 100
      - tingkat konversi saat ini (built+bare):  60% -> 100

    Rasional: risiko tutupan hutan tetap tinggi baik ketika lahan SEDANG
    ditebang cepat MAUPUN ketika sudah TERLANJUR dikonversi total. Tanpa
    komponen kedua, situs yang sudah jadi kawasan industri (loss-rate kecil
    karena hutannya sudah habis) keliru terbaca berisiko rendah.
    """
    loss_component = score_ipth(annual_loss_pct)              # 15%/th -> 100
    conv_component = min(converted_land_pct / 60.0 * 100, 100)  # 60% -> 100
    return round(max(loss_component, conv_component), 1)


def realized_impact_score(converted_land_pct: float,
                          annual_loss_pct: float) -> float:
    """
    Skor 'dampak terealisasi': kerusakan lingkungan yang SUDAH terjadi, dari
    konversi lahan permanen (built+bare) dan/atau laju kehilangan hutan terbaru.
    Diambil maksimum dari keduanya.

    Tujuannya menjamin situs yang sudah rusak parah (mis. kawasan industri yang
    dulunya hutan) tidak ter-dilusi menjadi 'risiko menengah' hanya karena
    faktor lokasi (lereng landai, jauh dari kawasan lindung formal) kebetulan
    rendah. Skor akhir = max(skor tertimbang, skor dampak terealisasi).
    """
    conv = min((converted_land_pct or 0) * 1.15, 100.0)  # ~87% terkonversi -> 100
    loss = score_ipth(annual_loss_pct or 0)              # 15%/th -> 100
    return round(max(conv, loss), 1)


def score_from_baseline(baseline: dict) -> dict:
    """
    Hitung skor risiko dari baseline satelit NYATA (hasil precompute / GEE live).

    `baseline` mengikuti skema dari data_provider.get_baseline():
        landcover {kelas: %}, slope, water, tree_loss, protected, biodiversity.

    Skor akhir = max(skor tertimbang 5-faktor, skor dampak terealisasi), agar
    mencerminkan kerentanan lokasi MAUPUN kerusakan yang sudah nyata.
    """
    lc = baseline.get("landcover", {})
    slope = baseline.get("slope", {})
    water = baseline.get("water", {})
    tl = baseline.get("tree_loss", {})
    prot = baseline.get("protected", {})
    bio = baseline.get("biodiversity", {})

    # IKKL: bedakan "data tidak tersedia" (default medium) vs "tidak ada dalam
    # jangkauan" (risiko rendah / jauh).
    dist = prot.get("distance_km")
    if dist is None and "tidak ada" in str(prot.get("source", "")).lower():
        dist = 30.0

    conv = converted_pct(lc)
    annual_loss = tl.get("annual_loss_pct", 0) or 0
    sub = {
        "IPTH": score_ipth_v2(annual_loss, conv),
        "IKH":  score_ikh(water.get("water_within_polygon_pct", 0) or 0,
                          nearest_water_m=water.get("nearest_water_m"),
                          near_river_flag=bool(water.get("near_river", False))),
        "ISR":  score_isr(slope.get("steep_pct", 0) or 0),
        "IKKL": score_ikkl(distance_to_protected_km=dist,
                           overlap_with_protected=bool(prot.get("overlap", False))),
        "ISB":  score_isb(regional_prior=float(bio.get("score", 55))),
    }
    sub = {k: round(v, 1) for k, v in sub.items()}

    result = compute_total_score(sub)             # skor tertimbang 5-faktor
    weighted_total = result["total"]
    realized = realized_impact_score(conv, annual_loss)
    final = round(max(weighted_total, realized), 1)
    label, color, status_text = classify_risk(final)

    result.update({
        "total": final,
        "label": label,
        "color": color,
        "status_text": status_text,
        "weighted_total": weighted_total,
        "realized_impact": realized,
        # Only flag escalation when realized impact is MEANINGFULLY higher than
        # the weighted score (avoids a noisy note when the two nearly tie).
        "escalated": realized > weighted_total + 5.0,
        "converted_pct": round(conv, 1),
    })
    return result
