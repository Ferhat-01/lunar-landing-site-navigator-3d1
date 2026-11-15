import time
import threading
import numpy as np
import pandas as pd
from astroquery.jplhorizons import Horizons
from astropy.time import Time

_REF_LAT = -89.54
_REF_LON = 129.78
_MOON_EARTH_PARALLAX = 1737.4 / 384400.0
_HORIZONS_LOCK = threading.Lock()
_BASE_EPH_CACHE = {}


def _enu_basis(lat_deg: float, lon_deg: float):
    """Ay-sabit (Moon-fixed) koordinatlarda verilen (lat, lon) noktası için (Doğu, Kuzey, Yukarı) birim vektörlerini döner."""
    phi = np.deg2rad(lat_deg)
    lam = np.deg2rad(lon_deg)
    sin_p, cos_p = np.sin(phi), np.cos(phi)
    sin_l, cos_l = np.sin(lam), np.cos(lam)
    east = np.array([-sin_l, cos_l, 0.0], dtype=float)
    north = np.array([-sin_p * cos_l, -sin_p * sin_l, cos_p], dtype=float)
    up = np.array([cos_p * cos_l, cos_p * sin_l, sin_p], dtype=float)
    return east, north, up


def _azel_to_vectors(az_deg: np.ndarray, el_deg: np.ndarray, lat_deg: float, lon_deg: float) -> np.ndarray:
    """Yerel (Azimut, Yükseklik) dizilerini Ay-sabit 3B birim vektörlere (N x 3) dönüştürür."""
    east, north, up = _enu_basis(lat_deg, lon_deg)
    az = np.deg2rad(az_deg)
    el = np.deg2rad(el_deg)
    cos_e = np.cos(el)
    return (
        (cos_e * np.cos(az))[:, None] * north[None, :]
        + (cos_e * np.sin(az))[:, None] * east[None, :]
        + np.sin(el)[:, None] * up[None, :]
    )


def _vectors_to_azel(vecs: np.ndarray, lat_deg: float, lon_deg: float):
    """Ay-sabit 3B vektörleri (N x 3) hedef (lat, lon) için yerel (Azimut, Yükseklik) derecelerine dönüştürür."""
    east, north, up = _enu_basis(lat_deg, lon_deg)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    unit = vecs / np.maximum(norms, 1e-12)
    e_comp = unit @ east
    n_comp = unit @ north
    u_comp = np.clip(unit @ up, -1.0, 1.0)
    az = np.rad2deg(np.arctan2(e_comp, n_comp)) % 360.0
    el = np.rad2deg(np.arcsin(u_comp))
    return az, el


def _analytical_moon_vectors(t_start: Time, duration_days: int):
    """NASA JPL Horizons erişilemediğinde Cassini yasaları ve Ay librasyonu ile analitik yedek efemeris üretir."""
    hours = int(duration_days) * 24 + 1
    times = t_start + (np.arange(hours) / 24.0)
    d = times.jd - 2451545.0

    # Ay ortalama elemanları (IAU / Meeus)
    sun_anom = np.deg2rad(357.528 + 0.9856003 * d)
    sun_ecl_lon = np.deg2rad(280.460 + 0.9856474 * d + 1.915 * np.sin(sun_anom))
    moon_mean_lon = np.deg2rad(218.3165 + 13.17639648 * d)
    omega_node = np.deg2rad(125.0445 - 0.05295377 * d)
    moon_anom = np.deg2rad(134.963 + 13.064993 * d)
    moon_arg_lat = np.deg2rad(93.272 + 13.229350 * d)

    # Güneş selenografik boylam ve enlemi (1.5424° eksen eğikliği dahil)
    lam_sun = np.pi - (moon_mean_lon - sun_ecl_lon)
    beta_sun = np.deg2rad(1.5424) * np.sin(sun_ecl_lon - omega_node)
    sun_vecs = np.column_stack([
        np.cos(beta_sun) * np.cos(lam_sun),
        np.cos(beta_sun) * np.sin(lam_sun),
        np.sin(beta_sun),
    ])

    # Dünya optik librasyonu (±6.3° boylam, ±6.7° enlem)
    l_lon = np.deg2rad(6.29) * np.sin(moon_anom)
    l_lat = np.deg2rad(-6.68) * np.sin(moon_arg_lat)
    earth_vecs = np.column_stack([
        np.cos(l_lat) * np.cos(l_lon),
        np.cos(l_lat) * np.sin(l_lon),
        np.sin(l_lat),
    ])

    dt_series = pd.to_datetime([t.iso[:16] for t in times])
    return dt_series, sun_vecs, earth_vecs


def _fetch_base_ephemeris(start_date: str, duration_days: int):
    """(start_date, duration_days) için referans efemerisi iş parçacığı güvenli önbellekten veya JPL'den getirir."""
    key = (start_date, int(duration_days))
    cached = _BASE_EPH_CACHE.get(key)
    if cached is not None:
        return cached

    with _HORIZONS_LOCK:
        cached = _BASE_EPH_CACHE.get(key)
        if cached is not None:
            return cached

        t_start = Time(f"{start_date} 00:00:00", scale='utc')
        t_end = t_start + duration_days
        epochs = {
            'start': t_start.iso[:16],
            'stop': t_end.iso[:16],
            'step': '1h'
        }
        lunar_site = {
            'lon': _REF_LON,
            'lat': _REF_LAT,
            'elevation': 0.0,
            'body': '301'
        }

        last_err = None
        for attempt in range(3):
            try:
                print(f"NASA JPL Horizons'a bağlanılıyor... Tarih: {start_date} ({duration_days}g, deneme {attempt + 1}/3)")
                sun_eph = Horizons(id='10', location=lunar_site, epochs=epochs).ephemerides(quantities='4').to_pandas()
                earth_eph = Horizons(id='399', location=lunar_site, epochs=epochs).ephemerides(quantities='4').to_pandas()
                dt_series = pd.to_datetime(sun_eph['datetime_str'])
                sun_vecs = _azel_to_vectors(sun_eph['AZ'].to_numpy(float), sun_eph['EL'].to_numpy(float), _REF_LAT, _REF_LON)
                earth_vecs = _azel_to_vectors(earth_eph['AZ'].to_numpy(float), earth_eph['EL'].to_numpy(float), _REF_LAT, _REF_LON)
                result = (dt_series, sun_vecs, earth_vecs)
                _BASE_EPH_CACHE[key] = result
                return result
            except Exception as exc:
                last_err = exc
                time.sleep(0.6 * (attempt + 1))

        print(f"[UYARI] NASA JPL Horizons erişimi geçici olarak yanıt vermedi ({last_err}); analitik yedek efemeris kullanılıyor.")
        result = _analytical_moon_vectors(t_start, duration_days)
        _BASE_EPH_CACHE[key] = result
        return result


def get_lunar_sky_data(lat: float, lon: float, start_date: str, duration_days: int = 14):
    """
    Seçilen Ay koordinatı (lat, lon) ve tarih aralığı için NASA JPL Horizons'dan
    saatlik Güneş ve Dünya (Azimut, Yükseklik Açısı) verilerini döndürür.
    """
    dt_series, sun_vecs, earth_vecs = _fetch_base_ephemeris(start_date, duration_days)

    _, _, up_ref = _enu_basis(_REF_LAT, _REF_LON)
    _, _, up_tgt = _enu_basis(lat, lon)
    earth_parallax = earth_vecs + _MOON_EARTH_PARALLAX * (up_ref - up_tgt)[None, :]

    sun_az, sun_el = _vectors_to_azel(sun_vecs, lat, lon)
    earth_az, earth_el = _vectors_to_azel(earth_parallax, lat, lon)

    return pd.DataFrame({
        'datetime_utc': dt_series,
        'sun_az': sun_az,
        'sun_el': sun_el,
        'earth_az': earth_az,
        'earth_el': earth_el
    })


if __name__ == "__main__":
    df_test = get_lunar_sky_data(lat=-89.54, lon=129.78, start_date="2026-11-15", duration_days=14)
    print("\n--- İLK 10 SAATLİK VERİ ---")
    print(df_test.head(10).to_string(index=False))
    print("\n--- ÖZET İSTATİSTİKLER ---")
    print(f"Maksimum Güneş Açısı: {df_test['sun_el'].max():.2f}°")
    print(f"Minimum Güneş Açısı:  {df_test['sun_el'].min():.2f}°")
    print(f"Dünya Açısı Aralığı:  {df_test['earth_el'].min():.2f}° ile {df_test['earth_el'].max():.2f}° arası")
