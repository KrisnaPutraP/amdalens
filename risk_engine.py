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


def score_ikh(water_within_pct: float, near_river_flag: bool = False) -> float:
    """
    IKH: Indeks Kerentanan Hidrologi.
    Proxy sederhana: % badan air dalam polygon + flag kedekatan sungai.
    Area dengan sungai permanen + rawan banjir tinggi = 100.

    Untuk MVP, kami pakai aproksimasi: water_within_pct.
    Di versi produksi akan ditambah layer sungai OSM dan zona banjir BNPB.
    """
    # Base score dari water coverage
    base = min(water_within_pct * 20, 80)  # 5% water = 100, capped at 80
    if near_river_flag:
        base = min(base + 20, 100)
    return round(base, 2)


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


def score_isb(biodiversity_overlap_pct: float = None) -> float:
    """
    ISB: Indeks Sensitivitas Biodiversitas.
    Overlap polygon dengan habitat spesies terancam (IUCN) atau KBA.
    Untuk MVP: default proxy berdasarkan regional biodiversity priors.
    Morowali area Sulawesi = high biodiversity baseline.
    """
    if biodiversity_overlap_pct is not None:
        return min(biodiversity_overlap_pct * 2, 100)  # 50% overlap = 100
    # Fallback: medium-high for tropical Indonesia areas
    return 55.0


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


# ============ MOCK MODE untuk demo tanpa GEE ============
def mock_score_morowali() -> dict:
    """
    Mock sub-indices yang dirancang untuk menghasilkan KRITIS pada demo Morowali.
    Digunakan jika GEE tidak tersedia atau untuk smoke-testing UI.
    Angka-angka ini berdasarkan estimasi kualitatif dari literatur publik
    tentang Bahodopi yaitu area dengan perubahan tutupan lahan signifikan.
    Target: skor total sekitar 78 (KRITIS), konsisten dengan skenario proposal.
    """
    sub = {
        "IPTH": 88,   # area dengan deforestasi tinggi (bobot 0.30)
        "IKH":  72,   # dekat sungai permanen, rawan banjir (bobot 0.25)
        "ISR":  62,   # 22% area curam >30 derajat (bobot 0.20)
        "IKKL": 78,   # 3.2 km ke kawasan lindung, kategori dekat (bobot 0.15)
        "ISB":  80,   # Sulawesi Wallacea biodiversity hotspot (bobot 0.10)
    }
    return compute_total_score(sub)


def mock_score_reference() -> dict:
    """Mock low-risk reference area for comparison."""
    sub = {
        "IPTH": 10,
        "IKH":  20,
        "ISR":  25,
        "IKKL": 30,
        "ISB":  55,
    }
    return compute_total_score(sub)
