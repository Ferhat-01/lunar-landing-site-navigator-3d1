from fastapi import FastAPI, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional
import os
import re
import html
import json
import urllib.request
import urllib.error
from mission_analyzer import ARTEMIS_SITES, analyze_mission, get_terrain_3d_data

app = FastAPI(title="NASA Space Apps 2026 - Lunar Landing Site Navigator")

ANALYSIS_CACHE = {}
AI_COMMENT_CACHE = {}
def _load_env_key(var_name: str) -> str:
    val = os.environ.get(var_name, "").strip()
    if val:
        return val
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{var_name}="):
                        return line.split("=", 1)[1].strip().strip('"').strip("'")
        except Exception:
            pass
    return ""

GEMINI_API_KEY = _load_env_key("GEMINI_API_KEY")
GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.8-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-3-flash-preview"
]

os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def read_index():
    return FileResponse("static/index.html")

@app.get("/api/sites")
def get_sites():
    return get_terrain_3d_data()["sites"]

@app.get("/api/terrain3d")
def api_terrain_3d():
    return get_terrain_3d_data()

@app.get("/api/analyze")
def api_analyze(
    site_id: str,
    start_date: str = "2026-11-15",
    start_time: str = "00:00",
    duration_days: int = 14,
    custom_lat: Optional[float] = None,
    custom_lon: Optional[float] = None
):
    if site_id != "custom" and site_id not in ARTEMIS_SITES:
        raise HTTPException(status_code=404, detail="İniş bölgesi bulunamadı.")

    cache_key = f"{site_id}_{start_date}_{start_time}_{duration_days}_{custom_lat}_{custom_lon}"
    if cache_key not in ANALYSIS_CACHE:
        try:
            ANALYSIS_CACHE[cache_key] = analyze_mission(
                site_id=site_id,
                start_date=start_date,
                duration_days=duration_days,
                start_time=start_time,
                custom_lat=custom_lat,
                custom_lon=custom_lon
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Analiz sırasında sunucu hatası: {e}")

    return ANALYSIS_CACHE[cache_key]

@app.get("/api/compare")
def api_compare(
    site_a: str,
    date_a: str = "2026-11-15",
    time_a: str = "00:00",
    site_b: str = "nobile_rim_1",
    date_b: str = "2026-11-15",
    time_b: str = "00:00",
    duration_days: int = 14,
    custom_lat: Optional[float] = None,
    custom_lon: Optional[float] = None
):
    res_a = api_analyze(site_a, date_a, time_a, duration_days, custom_lat, custom_lon)
    res_b = api_analyze(site_b, date_b, time_b, duration_days, None, None)
    return {"site_a": res_a, "site_b": res_b}

def _format_ai_html(text: str) -> str:
    cleaned = text.strip()
    cleaned = re.sub(r"^[:\-\*\s]+(?=(Seçenek|Genel|LUNA))", "", cleaned)
    cleaned = re.sub(r"(?m)^#{1,6}\s*(.+)$", r"**\1**", cleaned)
    safe = html.escape(cleaned)
    safe = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", safe)
    safe = re.sub(r"\n{2,}", "<br><br>", safe)
    safe = safe.replace("\n", "<br>")
    return safe


def _fallback_ai_comment(a: dict, b: dict, view_mode: str, question: str = "", lang: str = "tr") -> str:
    sa, ma = a.get("site", {}), a.get("metrics", {})
    sb, mb = b.get("site", {}), b.get("metrics", {})
    name_a = html.escape(str(sa.get("name", "Option A" if lang == "en" else "Seçenek A")))
    name_b = html.escape(str(sb.get("name", "Option B" if lang == "en" else "Seçenek B")))
    score_a = float(ma.get("feasibility_score", 0))
    score_b = float(mb.get("feasibility_score", 0))
    status_a = html.escape(str(ma.get("status", "")))
    status_b = html.escape(str(mb.get("status", "")))
    sun_a, sun_b = float(ma.get("sun_visibility_pct", 0)), float(mb.get("sun_visibility_pct", 0))
    sh_a, sh_b = int(ma.get("sun_hours", 0)), int(mb.get("sun_hours", 0))
    sel_a, sel_b = float(ma.get("avg_sun_elevation_deg", 0)), float(mb.get("avg_sun_elevation_deg", 0))
    ss_a, ss_b = int(ma.get("hours_to_sunset", 0)), int(mb.get("hours_to_sunset", 0))
    dark_a, dark_b = int(ma.get("max_dark_streak_hours", 0)), int(mb.get("max_dark_streak_hours", 0))
    earth_a, earth_b = float(ma.get("earth_comm_pct", 0)), float(mb.get("earth_comm_pct", 0))
    es_a, es_b = int(ma.get("hours_to_earthset", 0)), int(mb.get("hours_to_earthset", 0))
    slope_a, slope_b = float(sa.get("slope_deg", 0)), float(sb.get("slope_deg", 0))
    elev_a, elev_b = float(sa.get("elevation_km", 0)), float(sb.get("elevation_km", 0))
    ice_a = html.escape(str(ma.get("water_ice_potential", "Belirtilmemiş")))
    ice_b = html.escape(str(mb.get("water_ice_potential", "Belirtilmemiş")))

    if lang == "en":
        if abs(score_a - score_b) < 0.5:
            sec1 = (
                f"🏆 <strong>1. Overall Decision & Mission Recommendation:</strong> <strong>{name_a}</strong> ({score_a} pts — {status_a}) and "
                f"<strong>{name_b}</strong> ({score_b} pts — {status_b}) are nearly tied in overall mission feasibility. "
                f"Battery survival capacity and relay satellite availability should guide the final selection."
            )
        elif score_a > score_b:
            sec1 = (
                f"🏆 <strong>1. Overall Decision & Mission Recommendation:</strong> <strong>Option A ({name_a})</strong> outperforms "
                f"<strong>Option B ({name_b})</strong> ({score_b} pts) by <strong>+{(score_a - score_b):.1f} points</strong> with <strong>{score_a} pts</strong> ({status_a}) "
                f"and is recommended as the primary landing target."
            )
        else:
            sec1 = (
                f"🏆 <strong>1. Overall Decision & Mission Recommendation:</strong> <strong>Option B ({name_b})</strong> outperforms "
                f"<strong>Option A ({name_a})</strong> ({score_a} pts) by <strong>+{(score_b - score_a):.1f} points</strong> with <strong>{score_b} pts</strong> ({status_b}) "
                f"and is recommended as the primary landing target."
            )
        better_sun_en = "Option A" if sun_a >= sun_b else "Option B"
        worst_dark = max(dark_a, dark_b)
        dark_warn_en = (
            f"A maximum continuous shadow of <strong>{worst_dark} hours</strong> poses a severe -233°C thermal and battery depletion risk, requiring RHU/RTG heaters or hibernation mode."
            if worst_dark > 48
            else "Continuous darkness duration remains within manageable battery limits at both sites."
        )
        sec2 = (
            f"☀️ <strong>2. Solar Power & Thermal Survival:</strong> Option A provides <strong>{sun_a}%</strong> illumination ({sh_a} hrs | Avg Sun el: {sel_a}° | First sunset: {ss_a} hrs | Max dark: {dark_a} hrs), "
            f"while Option B provides <strong>{sun_b}%</strong> ({sh_b} hrs | Avg Sun el: {sel_b}° | First sunset: {ss_b} hrs | Max dark: {dark_b} hrs). "
            f"<strong>{better_sun_en}</strong> leads in solar power continuity. {dark_warn_en}"
        )
        relay_en = (
            "Because local crater rims occlude Earth for extended periods, an orbital <strong>Relay Satellite (LunaNet / Queqiao-2)</strong> is required."
            if min(earth_a, earth_b) < 75
            else "Direct-To-Earth (DTE / NASA DSN) communication windows are strong at both candidates."
        )
        sec3 = (
            f"📡 <strong>3. Direct-To-Earth (DTE) Comm & Libration:</strong> Earth visibility is <strong>{earth_a}%</strong> at Option A (first blackout in {es_a} hrs) "
            f"and <strong>{earth_b}%</strong> at Option B (first blackout in {es_b} hrs), with ~1.28s OWLT delay and ±6°–±8° lunar libration active. {relay_en}"
        )
        safer_slope_en = "Option A" if slope_a <= slope_b else "Option B"
        sec4 = (
            f"🏔️ <strong>4. LOLA Topography & ❄️ Water Ice (PSR) Value:</strong> Option A has a <strong>{slope_a}°</strong> slope at <strong>{elev_a} km</strong> elevation, "
            f"while Option B has a <strong>{slope_b}°</strong> slope at <strong>{elev_b} km</strong> elevation. "
            f"<strong>{safer_slope_en}</strong> offers flatter terrain for touchdown stability (critical limit: 15°)."
        )
        sec5 = (
            f"⚠️ <strong>5. Engineering Recommendation:</strong> Lock in <strong>{'Option A' if score_a >= score_b else 'Option B'}</strong> as the baseline landing zone "
            f"and schedule primary PSR volatile/water-ice sampling during the initial sunlit charging window."
        )
        if question:
            q_safe = html.escape(question)
            return f"💬 <strong>Question:</strong> <em>\"{q_safe}\"</em><br><br>{sec1}<br><br>{sec2}<br><br>{sec3}<br><br>{sec4}<br><br>{sec5}"
        return f"{sec1}<br><br>{sec2}<br><br>{sec3}<br><br>{sec4}<br><br>{sec5}"

    if abs(score_a - score_b) < 0.5:
        sec1 = (
            f"🏆 <strong>1. Genel Karar & Görev Önerisi:</strong> <strong>{name_a}</strong> ({score_a} puan — {status_a}) ile "
            f"<strong>{name_b}</strong> ({score_b} puan — {status_b}) toplam görev uygulanabilirliğinde başa baş düzeydedir. "
            f"Tercih yapılırken batarya sağkalım kapasitesi ve röle uydusu erişimi belirleyici olmalıdır."
        )
    elif score_a > score_b:
        sec1 = (
            f"🏆 <strong>1. Genel Karar & Görev Önerisi:</strong> <strong>Seçenek A ({name_a})</strong>, <strong>{score_a} puan</strong> ({status_a}) ile "
            f"<strong>Seçenek B ({name_b})</strong> seçeneğine ({score_b} puan — {status_b}) kıyasla <strong>+{(score_a - score_b):.1f} puan</strong> daha üstündür ve "
            f"birincil iniş bölgesi olarak önerilir."
        )
    else:
        sec1 = (
            f"🏆 <strong>1. Genel Karar & Görev Önerisi:</strong> <strong>Seçenek B ({name_b})</strong>, <strong>{score_b} puan</strong> ({status_b}) ile "
            f"<strong>Seçenek A ({name_a})</strong> seçeneğine ({score_a} puan — {status_a}) kıyasla <strong>+{(score_b - score_a):.1f} puan</strong> daha güvenlidir ve "
            f"birincil iniş hedefi olarak seçilmelidir."
        )

    better_sun = "Seçenek A" if sun_a >= sun_b else "Seçenek B"
    worst_dark = max(dark_a, dark_b)
    dark_warn = (
        f"Özellikle <strong>{worst_dark} saatlik</strong> kesintisiz krater gölgesi, standart lityum-iyon bataryaların tükenmesine ve -233°C termal şoka yol açabileceğinden radyoizotop ısıtıcı (RHU/RTG) veya uyku modu zorunludur."
        if worst_dark > 48
        else "Her iki bölgede de kesintisiz karanlık süresi yönetilebilir batarya sınırları içindedir."
    )
    sec2 = (
        f"☀️ <strong>2. Güneş Enerjisi & Termal Sağkalım:</strong> Seçenek A görev süresince <strong>%{sun_a}</strong> ({sh_a} saat | Ort. Güneş açısı: {sel_a}° | İlk batış: {ss_a} sa | Maks. karanlık: {dark_a} sa), "
        f"Seçenek B ise <strong>%{sun_b}</strong> ({sh_b} saat | Ort. Güneş açısı: {sel_b}° | İlk batış: {ss_b} sa | Maks. karanlık: {dark_b} sa) aydınlanma sağlar. "
        f"Enerji sürekliliğinde <strong>{better_sun}</strong> avantajlıdır. {dark_warn}"
    )

    relay_note = (
        "Krater duvarı Dünya'yı uzun süre perdelediği için kesintisiz telemetri adına yörüngede <strong>Röle Uydusu (LunaNet / Queqiao-2)</strong> desteği şarttır."
        if min(earth_a, earth_b) < 75
        else "Doğrudan Dünya İletişimi (DTE / NASA DSN) pencereleri her iki seçenekte de yüksek süreklilik sunmaktadır."
    )
    sec3 = (
        f"📡 <strong>3. Dünya İletişimi (DTE) & Librasyon:</strong> Doğrudan Dünya görünürlüğü A'da <strong>%{earth_a}</strong> (ilk kesintiye {es_a} saat), "
        f"B'de <strong>%{earth_b}</strong> (ilk kesintiye {es_b} saat) düzeyindedir (~1.28 sn tek yön ışık hızı gecikmesi ve ±6°–±8° Ay librasyon salınımı aktif). {relay_note}"
    )

    safer_slope = "Seçenek A" if slope_a <= slope_b else "Seçenek B"
    sec4 = (
        f"🏔️ <strong>4. LOLA Topografya & ❄️ Su Buzu (PSR) Değeri:</strong> Seçenek A <strong>{slope_a}°</strong> eğim ve <strong>{elev_a} km</strong> rakıma ({ice_a}), "
        f"Seçenek B ise <strong>{slope_b}°</strong> eğim ve <strong>{elev_b} km</strong> rakıma ({ice_b}) sahiptir. "
        f"İniş mekaniği ve devrilme güvenliği açısından <strong>{safer_slope}</strong> daha düz bir zemin sunar (kritik limit: 15°)."
    )

    sec5 = (
        f"⚠️ <strong>5. Mühendislik Tavsiyesi:</strong> Görev planlamasında "
        f"{'Seçenek A' if score_a >= score_b else 'Seçenek B'} ana hedef olarak kilitlenmeli; "
        f"inişten hemen sonraki ilk aydınlık pencerede güneş panelleri tam kapasite şarj edilerek PSR su buzu örnekleme rotası tamamlanmalıdır."
    )

    if question:
        q_safe = html.escape(question)
        return f"💬 <strong>Soru:</strong> <em>\"{q_safe}\"</em><br><br>{sec1}<br><br>{sec2}<br><br>{sec3}<br><br>{sec4}<br><br>{sec5}"
    return f"{sec1}<br><br>{sec2}<br><br>{sec3}<br><br>{sec4}<br><br>{sec5}"


@app.post("/api/ai-comment")
def api_ai_comment(payload: dict = Body(...)):
    site_a = payload.get("site_a") or {}
    site_b = payload.get("site_b") or {}
    view_mode = payload.get("view_mode", "eng")
    lang = str(payload.get("lang", "tr") or "tr").lower()
    if lang not in ("tr", "en"):
        lang = "tr"
    question = str(payload.get("question", "") or "").strip()
    force = bool(payload.get("force", False))

    sa, ma = site_a.get("site", {}), site_a.get("metrics", {})
    sb, mb = site_b.get("site", {}), site_b.get("metrics", {})
    cache_key = (
        sa.get("id"), sa.get("lat"), sa.get("lon"), site_a.get("start_date"),
        sb.get("id"), sb.get("lat"), sb.get("lon"), site_b.get("start_date"),
        view_mode, lang, question
    )
    if not force and cache_key in AI_COMMENT_CACHE:
        return AI_COMMENT_CACHE[cache_key]

    if lang == "en":
        tone_desc = (
            "Education & Public mode: Write in clear, engaging, and accessible English suitable for students, educators, and the general public."
            if view_mode == "edu"
            else "Engineering mode: Write in quantitative, concise, decision-oriented technical English for NASA lunar mission planners."
        )
        task_instruction = (
            f"Answer the user's question based on the real numerical telemetry of the two landing options in a complete 4-6 sentence English paragraph: \"{question}\""
            if question
            else (
                "Compare Option A and Option B in detail using the real LOLA and JPL Horizons data above. "
                "Write a complete, non-truncated analysis in English under these exact 5 headings:\n"
                "1) **🏆 1. Overall Decision & Mission Recommendation:** (Score difference, GO/CAUTION/NO-GO status, and primary target selection)\n"
                "2) **☀️ 2. Solar Power, Thermal Survival & Battery Budget:** (Illumination %, hours, average Sun angle, hours to sunset, and max continuous darkness risk)\n"
                "3) **📡 3. Direct-To-Earth (DTE) Comm, Libration & Relay Need:** (DTE %, first blackout hour, ~1.28s OWLT delay, and whether a relay satellite is required)\n"
                "4) **🏔️ 4. LOLA Topography, Slope & ❄️ Water Ice (PSR) Value:** (Slope angles vs. 15° tipping limit, elevation, and PSR water-ice access)\n"
                "5) **⚠️ 5. Critical Mission Risk & Engineering Recommendation:** (Actionable recommendation for launch window, thermal/battery design, and surface ops)"
            )
        )
    else:
        tone_desc = (
            "Eğitim & Halk modu: Hem bilimsel açıdan zengin hem de öğrencilerin ve halkın kolayca anlayacağı akıcı, açıklayıcı Türkçe kullan."
            if view_mode == "edu"
            else "Mühendislik modu: NASA görev planlayıcılarına yönelik kapsamlı, nicel (sayısal değerleri kıyaslayan), teknik ve karar odaklı Türkçe kullan."
        )
        task_instruction = (
            f"Kullanıcının şu sorusunu yukarıdaki iki iniş seçeneğinin gerçek sayısal verilerine dayanarak 4-6 cümlelik kapsamlı, net ve eksiksiz bir paragrafla yanıtla: \"{question}\""
            if question
            else (
                "Seçenek A ve Seçenek B'yi yukarıdaki gerçek LOLA ve JPL Horizons verileriyle detaylıca kıyasla. "
                "Cümleleri yarıda bırakmadan, eksiksiz ve doyurucu şekilde tam olarak şu 5 başlıkta yaz:\n"
                "1) **🏆 1. Genel Karar & Görev Önerisi:** (Puan farkı, GO/CAUTION/NO-GO durumu ve hangi seçeneğin neden seçilmesi gerektiği)\n"
                "2) **☀️ 2. Güneş Enerjisi, Termal Sağkalım & Batarya Bütçesi:** (Güneş yüzdesi/saati, ortalama açı, ilk batışa kalan süre ve maksimum karanlık süresinin batarya/donma riskine etkisi)\n"
                "3) **📡 3. Dünya İletişimi (DTE), Librasyon & Röle İhtiyacı:** (DTE yüzdesi, ilk kesinti saati, ~1.28 sn gecikme ve krater engeli nedeniyle röle uydusu gerekip gerekmediği)\n"
                "4) **🏔️ 4. LOLA Topografya, İniş Eğimi & ❄️ Su Buzu (PSR) Değeri:** (Eğim dereceleri, 15° devrilme sınırı, rakım ve kalıcı gölge su buzu potansiyeli)\n"
                "5) **⚠️ 5. Kritik Görev Riski & Mühendislik Tavsiyesi:** (Fırlatma penceresi, batarya/ısıtıcı tasarımı ve operasyon için somut öneri)"
            )
        )

    prompt = f"""You are LUNA — NASA Lunar South Pole Mission Analyst Mascot.
{tone_desc}

Option A (Seçenek A): {sa.get('name')} ({sa.get('lat')}°S, {sa.get('lon')}°E) | Start: {site_a.get('start_date')} UTC
- Score/Status: {ma.get('feasibility_score')} ({ma.get('status')})
- Sun: %{ma.get('sun_visibility_pct')} ({ma.get('sun_hours')} hrs), Avg El: {ma.get('avg_sun_elevation_deg')}°, First Sunset: {ma.get('hours_to_sunset')} hrs, Max Dark: {ma.get('max_dark_streak_hours')} hrs
- Earth DTE: %{ma.get('earth_comm_pct')}, First Blackout: {ma.get('hours_to_earthset')} hrs
- LOLA Slope: {sa.get('slope_deg')}°, Elevation: {sa.get('elevation_km')} km, Water Ice/PSR: {ma.get('water_ice_potential')}

Option B (Seçenek B): {sb.get('name')} ({sb.get('lat')}°S, {sb.get('lon')}°E) | Start: {site_b.get('start_date')} UTC
- Score/Status: {mb.get('feasibility_score')} ({mb.get('status')})
- Sun: %{mb.get('sun_visibility_pct')} ({mb.get('sun_hours')} hrs), Avg El: {mb.get('avg_sun_elevation_deg')}°, First Sunset: {mb.get('hours_to_sunset')} hrs, Max Dark: {mb.get('max_dark_streak_hours')} hrs
- Earth DTE: %{mb.get('earth_comm_pct')}, First Blackout: {mb.get('hours_to_earthset')} hrs
- LOLA Slope: {sb.get('slope_deg')}°, Elevation: {sb.get('elevation_km')} km, Water Ice/PSR: {mb.get('water_ice_potential')}

{task_instruction}"""

    for model in GEMINI_MODELS:
        gen_cfg = {
            "temperature": 0.35,
            "maxOutputTokens": 2048
        }
        if "preview" in model:
            gen_cfg["thinkingConfig"] = {"thinkingBudget": 0}
        req_body = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": gen_cfg
        }).encode("utf-8")
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        req = urllib.request.Request(url, data=req_body, headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=11) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                cand = (data.get("candidates") or [{}])[0]
                finish_reason = cand.get("finishReason", "")
                parts = cand.get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and not p.get("thought")).strip()
                min_len = 40 if question else 250
                if text and len(text) >= min_len and finish_reason != "MAX_TOKENS":
                    out = {"comment": _format_ai_html(text), "source": f"Gemini AI ({model})", "live": True}
                    AI_COMMENT_CACHE[cache_key] = out
                    return out
                print(f"[Gemini {model}] yanıt kısa/kesik ({len(text)} krk, finish={finish_reason}), sonraki denenecek.")
        except Exception as exc:
            print(f"[Gemini {model}] atlandı: {exc}")

    fb_src = "LUNA Decision Engine (Full Analysis)" if lang == "en" else "LUNA Karar Motoru (Tam Analiz)"
    return {"comment": _fallback_ai_comment(site_a, site_b, view_mode, question, lang), "source": fb_src, "live": False}


def _start_public_tunnel(port: int = 8000):
    import re
    import subprocess
    import threading
    import time

    def _runner():
        time.sleep(1.5)
        while True:
            current_url = [None]
            stop_ping = [False]

            def _keepalive():
                while not stop_ping[0]:
                    time.sleep(40)
                    if stop_ping[0] or not current_url[0]:
                        continue
                    try:
                        req = urllib.request.Request(
                            current_url[0] + "/api/sites",
                            headers={"User-Agent": "LunarNavigator-KeepAlive"}
                        )
                        with urllib.request.urlopen(req, timeout=8) as _:
                            pass
                    except Exception:
                        pass

            ping_thread = threading.Thread(target=_keepalive, daemon=True)
            ping_thread.start()
            try:
                proc = subprocess.Popen(
                    [
                        "ssh", "-T",
                        "-o", "StrictHostKeyChecking=no",
                        "-o", "ServerAliveInterval=30",
                        "-R", f"80:127.0.0.1:{port}",
                        "nokey@localhost.run"
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="ignore"
                )
                for line in proc.stdout:
                    m = re.search(r"https://[a-zA-Z0-9.-]+\.lhr\.life", line)
                    if m and m.group(0) != current_url[0]:
                        current_url[0] = m.group(0)
                        print("\n" + "=" * 66)
                        print("  [GENEL İNTERNET LİNKİ HAZIR - TELEFON / MOBİL VERİ / HER YERDEN]")
                        print(f"  -> {current_url[0]}")
                        print("=" * 66 + "\n", flush=True)
                proc.wait()
            except Exception as exc:
                print(f"[Tünel Uyarısı] SSH tüneli başlatılamadı: {exc}")
                break
            finally:
                stop_ping[0] = True
            time.sleep(3)

    t = threading.Thread(target=_runner, daemon=True)
    t.start()


def _free_port_if_busy(port: int = 8000):
    import subprocess
    import time
    my_pid = os.getpid()
    killed = set()
    try:
        out = subprocess.check_output(["netstat", "-ano"], text=True, errors="ignore")
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 5 and parts[0].upper() == "TCP":
                local_addr = parts[1]
                state = parts[3].upper()
                if local_addr.endswith(f":{port}") and ("LISTEN" in state or state == "LISTENING"):
                    try:
                        pid = int(parts[-1])
                        if pid > 0 and pid != my_pid and pid not in killed:
                            subprocess.run(["taskkill", "/F", "/PID", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            killed.add(pid)
                            print(f"  [Bilgi] 8000 portundaki eski sunucu kapatıldı (PID: {pid}).")
                    except ValueError:
                        pass
        if killed:
            time.sleep(0.8)
    except Exception:
        pass


if __name__ == "__main__":
    import socket
    import uvicorn
    _free_port_if_busy(8000)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            lan_ip = s.getsockname()[0]
    except Exception:
        lan_ip = "127.0.0.1"
    print("\n" + "=" * 66)
    print("  LUNAR NAVIGATOR SUNUCUSU BAŞLATILIYOR")
    print("  -> Bu bilgisayardan giriş : http://127.0.0.1:8000")
    print(f"  -> Aynı ağdan giriş       : http://{lan_ip}:8000")
    print("  -> İnternet tüneli (https): Otomatik bağlanıyor, birkaç sn bekleyin...")
    print("=" * 66 + "\n", flush=True)
    _start_public_tunnel(8000)
    uvicorn.run(app, host="0.0.0.0", port=8000)