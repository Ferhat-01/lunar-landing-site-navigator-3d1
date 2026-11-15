import os
import re
import time
import json
import urllib3
from urllib.parse import urljoin
import requests
import numpy as np

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

PDS_DIR_URL = "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/"
OUT_JSON = "nasa_lola_terrain.json"
LUNAR_RADIUS_KM = 1737.4

ARTEMIS_COORDS = {
    "shackleton_rim": {"lat": -89.54, "lon": 129.78},
    "malapert_massif": {"lat": -85.95, "lon": 357.80},
    "connecting_ridge": {"lat": -89.45, "lon": 222.69},
    "faustini_rim_a": {"lat": -87.30, "lon": 77.00},
    "nobile_rim_1": {"lat": -85.20, "lon": 53.50}
}


def find_and_download_real_lola():
    # Klasörde daha önce tam inmiş bir ldem_80s_*.img varsa onu kullan
    for fn in os.listdir("."):
        if fn.lower().startswith("ldem_80s_") and fn.lower().endswith(".img") and os.path.getsize(fn) > 4_000_000:
            # Dosya boyutunun tam kare matris olup olmadığını kontrol et
            n_px = os.path.getsize(fn) // 2
            side = int(np.sqrt(n_px))
            if side * side == n_px:
                print(f"[OK] Mevcut eksiksiz NASA LOLA dosyası kullanılıyor: {fn} ({side}x{side} px)")
                return fn

    print("NASA PDS resmi LOLA dizinindeki mevcut dosyalar listeleniyor...")
    r = requests.get(PDS_DIR_URL, timeout=25, verify=False)
    r.raise_for_status()

    # Dizindeki tüm ldem_80s_*.img dosyalarını bul
    hrefs = re.findall(r'href=["\']([^"\']*ldem_80s_[^"\']*\.img)["\']', r.text, re.IGNORECASE)
    if not hrefs:
        raise RuntimeError("NASA PDS dizininde ldem_80s_*.img bulunamadı.")

    # urljoin ile URL iki kez tekrarlanmadan tam adresi oluştur
    full_urls = sorted(list({urljoin(PDS_DIR_URL, h) for h in hrefs}))
    print("NASA sunucusunda bulunan gerçek dosyalar:")
    for u in full_urls:
        print("  -", os.path.basename(u))

    # En küçük boyutlu (en hızlı inecek) dosyayı bulmak için HEAD isteği at (20m gibi 1.8 GB dosyaları ele)
    candidates = []
    for u in full_urls:
        try:
            head = requests.head(u, timeout=15, verify=False)
            size_bytes = int(head.headers.get("Content-Length", 0))
            if size_bytes > 0:
                candidates.append((size_bytes, u))
        except Exception:
            pass

    if not candidates:
        raise RuntimeError("Dosya boyutları sorgulanamadı.")

    candidates.sort(key=lambda x: x[0])  # En küçük dosyayı (ör. 150m/250m -> ~10-30 MB) en başa al
    expected_bytes, target_url = candidates[0]
    local_name = os.path.basename(target_url)
    total_mb = expected_bytes / (1024 * 1024)
    print(f"\n[SEÇİLDİ] En hızlı indirilecek gerçek NASA verisi: {local_name} ({total_mb:.2f} MB)")

    # Kesintiye dayanıklı (Resume destekli) indirme
    for attempt in range(1, 8):
        downloaded = os.path.getsize(local_name) if os.path.exists(local_name) else 0
        if downloaded >= expected_bytes:
            break
        headers = {"Range": f"bytes={downloaded}-"} if downloaded > 0 else {}
        try:
            with requests.get(target_url, headers=headers, stream=True, timeout=35, verify=False) as resp:
                if resp.status_code not in (200, 206):
                    raise RuntimeError(f"HTTP {resp.status_code}")
                mode = "ab" if resp.status_code == 206 else "wb"
                with open(local_name, mode) as f:
                    for chunk in resp.iter_content(chunk_size=131072):
                        if chunk:
                            f.write(chunk)
                now_mb = os.path.getsize(local_name) / (1024 * 1024)
                print(f"  -> İndirildi: {now_mb:.2f} / {total_mb:.2f} MB")
        except Exception:
            now_mb = os.path.getsize(local_name) / (1024 * 1024) if os.path.exists(local_name) else 0
            print(f"  -> Bağlantı tazeleniyor ({now_mb:.2f}/{total_mb:.2f} MB), devam ediliyor...")
            time.sleep(1)

    if not os.path.exists(local_name) or os.path.getsize(local_name) < expected_bytes:
        raise RuntimeError("İndirme tamamlanamadı, lütfen komutu tekrar çalıştırın (kaldığı yerden devam edecektir).")

    print(f"[OK] %100 Gerçek NASA LOLA DEM indirildi: {local_name}")
    return local_name


def latlon_to_polar_xy_km(lat: float, lon: float):
    r_km = (90.0 - abs(lat)) * (np.pi / 180.0) * LUNAR_RADIUS_KM
    rad = np.deg2rad(lon)
    return r_km * np.cos(rad), r_km * np.sin(rad)


def compute_true_horizon_360(dem_m: np.ndarray, pixel_size_km: float, center_row: int, center_col: int):
    rows, cols = dem_m.shape
    h0 = float(dem_m[center_row, center_col])

    dz_dy = (float(dem_m[center_row + 1, center_col]) - float(dem_m[center_row - 1, center_col])) / (
                2 * pixel_size_km * 1000.0)
    dz_dx = (float(dem_m[center_row, center_col + 1]) - float(dem_m[center_row, center_col - 1])) / (
                2 * pixel_size_km * 1000.0)
    slope_deg = round(float(np.rad2deg(np.arctan(np.hypot(dz_dx, dz_dy)))), 2)

    horizon_360 = []
    max_steps = int(round(36.0 / pixel_size_km))
    steps = np.arange(1, max_steps)
    distances_m = steps * pixel_size_km * 1000.0

    for az in range(360):
        rad = np.deg2rad(az)
        sample_cols = np.round(center_col + steps * np.sin(rad)).astype(int)
        sample_rows = np.round(center_row - steps * np.cos(rad)).astype(int)

        valid = (sample_rows >= 0) & (sample_rows < rows) & (sample_cols >= 0) & (sample_cols < cols)
        sample_rows = sample_rows[valid]
        sample_cols = sample_cols[valid]
        dists = distances_m[valid]

        heights = dem_m[sample_rows, sample_cols]
        curvature_drop_m = (dists ** 2) / (2.0 * LUNAR_RADIUS_KM * 1000.0)
        angles_deg = np.rad2deg(np.arctan2((heights - h0 - curvature_drop_m), dists))

        max_angle = float(np.max(angles_deg)) if len(angles_deg) > 0 else 0.0
        horizon_360.append(round(max_angle, 3))

    return horizon_360, slope_deg, round(h0 / 1000.0, 3)


def build_real_nasa_terrain():
    img_path = find_and_download_real_lola()

    raw = np.fromfile(img_path, dtype="<i2")
    side = int(np.sqrt(raw.size))
    dem_m = raw.reshape((side, side)).astype(np.float32) * 0.5  # NASA PDS standardı: DN * 0.5m

    mid_r, mid_c = side // 2, side // 2
    total_span_km = 2.0 * (10.0 * (np.pi / 180.0) * LUNAR_RADIUS_KM)
    pixel_size_km = total_span_km / side
    print(f"Gerçek NASA LOLA Matrisi: {side}x{side} px | Çözünürlük: {pixel_size_km * 1000:.1f} m/piksel")

    sites_real_data = {}
    for site_id, coord in ARTEMIS_COORDS.items():
        x_km, y_km = latlon_to_polar_xy_km(coord["lat"], coord["lon"])
        c_idx = int(round(mid_c + (x_km / pixel_size_km)))
        r_idx = int(round(mid_r - (y_km / pixel_size_km)))

        horizon_360, slope_deg, elev_km = compute_true_horizon_360(dem_m, pixel_size_km, r_idx, c_idx)
        sites_real_data[site_id] = {
            "x_km": round(x_km, 2),
            "y_km": round(y_km, 2),
            "elevation_km": elev_km,
            "slope_deg": slope_deg,
            "horizon_360": horizon_360
        }
        print(
            f"  -> {site_id}: Gerçek Yükseklik={elev_km} km | Eğim={slope_deg}° | Maks Ufuk Engeli={max(horizon_360):.2f}°")

    radius_px = int(round(160.0 / pixel_size_km))
    sub_dem = dem_m[mid_r - radius_px: mid_r + radius_px, mid_c - radius_px: mid_c + radius_px]

    grid_n = 90
    idx = np.linspace(0, sub_dem.shape[0] - 1, grid_n).astype(int)
    sampled_z_km = np.round(sub_dem[np.ix_(idx, idx)] / 1000.0, 3)
    sampled_z_km = np.flipud(sampled_z_km)
    axis_km = np.round(np.linspace(-160.0, 160.0, grid_n), 2).tolist()

    output_payload = {
        "source": f"NASA LRO LOLA GDR ({img_path}, {pixel_size_km * 1000:.0f}m/px Real PDS Data)",
        "sites": sites_real_data,
        "terrain_3d": {
            "axis_km": axis_km,
            "z_km": sampled_z_km.tolist()
        }
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output_payload, f)
    print(f"\n[BAŞARILI] %100 Gerçek NASA LOLA verisi '{OUT_JSON}' dosyasına kaydedildi!")


if __name__ == "__main__":
    build_real_nasa_terrain()