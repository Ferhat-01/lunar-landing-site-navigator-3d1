# 🌕 Project UluNova — Ay İniş Yeri Navigatörü 3D (Lunar Landing Site Navigator 3D)

### NASA LRO LOLA DEM (80m/px) & JPL Horizons Tabanlı 3B Ay Güney Kutbu Görev Planlama ve Karar Destek Sistemi
*Real-Time 3D Lunar South Pole Mission Planning & Feasibility Decision Engine — Developed for NASA Space Apps Challenge 2026*

[![Live Demo](https://img.shields.io/badge/🚀_CANLI_DEMO_/_LIVE_DEMO-TIKLA_VE_BAŞLAT_(OPEN_APP)-00c853?style=for-the-badge)](https://lunar-landing-site-navigator-3d1.onrender.com)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi)
![Three.js](https://img.shields.io/badge/Three.js-3D_WebGL-black?style=for-the-badge&logo=three.js)
![NASA Data](https://img.shields.io/badge/NASA_PDS-LOLA_80m_DEM-orange?style=for-the-badge)
![Gemini AI](https://img.shields.io/badge/LUNA_AI-Gemini_API-4285F4?style=for-the-badge)

---

## 🌐 Canlı Demo / Live Interactive Demo

👉 **Uygulamayı Kurulum Yapmadan Tarayıcıda Canlı Deneyin / Try Live in Browser:**  
### 🔗 [https://lunar-landing-site-navigator-3d1.onrender.com](https://lunar-landing-site-navigator-3d1.onrender.com)

> **💡 Not / Note:** Canlı demo ücretsiz bulut sunucusu (Render Free Tier) üzerinde barındırılmaktadır. İlk tıklamada sunucunun uykudan uyanması **~30–40 saniye** sürebilir; açıldıktan sonra tüm 3D simülasyonlar anlık çalışır.  
> *(Hosted on Render Free Tier — initial cold start may take ~30–40 seconds on first visit).*

---

## 📌 Proje Nedir? (What is Project UluNova?)

**Ay İniş Yeri Navigatörü 3D (Project UluNova)**, Ay'ın özellikle **Güney Kutbu**'nda gerçekleştirilecek insanlı (Artemis) ve insansız (CLPS, VIPER, Chang'e, LUPEX) uzay görevleri için en güvenli ve verimli iniş alanlarının belirlenmesine yardımcı olan **üç boyutlu, etkileşimli bir navigasyon, simülasyon ve karar destek platformudur.**

Ay'ın eksen eğikliği yalnızca **1.54°** olduğu için Güney Kutbu'nda Güneş hiçbir zaman tepeye yükselmez; ufuk çizgisini sıyırarak 360° döner. Bu durum:
- Yüksek krater sırtlarının neredeyse kesintisiz güneş enerjisi almasına,
- Sadece birkaç kilometre ötedeki krater çukurlarının ise **-233°C (40 K)** sıcaklıkta milyarlarca yıldır kalıcı gölgede (**PSR - Permanently Shadowed Regions**) kalmasına ve zengin **su buzu** barındırmasına yol açar.
- Ayrıca Dünya da kutup ufkunda **±6° ila ±8° librasyon (yalpalama)** hareketi yaptığı için bir krater dağı Dünya ile doğrudan iletişimi (**DTE**) aniden kesebilir.

**Project UluNova**, gerçek **NASA LRO LOLA** lazer altimetre topografya verilerini ve **NASA JPL Horizons** gezegen efemerislerini birleştirerek bu zorlu ortamı saat saat 3 boyutlu olarak simüle eder.

---

## 🎯 Kimlere Hitap Ediyor? (Target Audience)

Sistem, arayüzündeki çift modlu (**Mühendislik Modu** & **Eğitim/Halk Modu**) ve çift dilli (**TR / EN**) yapısıyla üç ana kitleye hitap eder:

1. **🛰️ Uzay Mühendisleri ve Görev Planlayıcılar (Engineering & Mission Planners):**
   - İniş bölgesi adaylarının saatlik güneşlenme yüzdesi, kesintisiz karanlık süresi (batarya ve RHU/RTG termal sağkalım bütçesi), gerçek LOLA yüzey eğimi (15° devrilme sınırı) ve Doğrudan Dünya İletişimi (DTE) pencerelerini sayısal olarak kıyaslamak isteyen uzmanlar.
   - Fırlatma ertelemelerinin (*örn. +7 gün gecikme*) görev başarısına etkisini saniyeler içinde test etmek isteyen karar vericiler.
2. **🎓 Akademisyenler, Üniversite Öğrencileri ve Araştırmacılar (Researchers & Students):**
   - Astronomi, uzay mühendisliği ve gezegen bilimi alanlarında Ay topografyası, yörünge mekaniği, librasyon ve PSR su buzu rezervleri üzerinde çalışan araştırmacılar (CSV telemetri dışa aktarım desteğiyle).
3. **🌍 Uzay Meraklıları, Öğretmenler ve Genel Halk (Educators & Public):**
   - *"Neden Ay Güney Kutbu'na gidiyoruz?"*, *"Apollo 11'in indiği ekvator ile Artemis'in ineceği Güney Kutbu arasındaki fark nedir?"* sorularını 3D WebGL simülasyonu, astronot kamerası ve yapay zeka rehberi (LUNA AI) ile deneyimleyerek öğrenmek isteyen herkes.

---

## ⚙️ Ne İşe Yarar ve Özellikleri Nelerdir? (Core Capabilities)

### 1. 🌍 3B Ay Güney Kutbu Topografya Haritası & 360° WebGL Uzay Simülasyonu
- **Gerçek NASA LOLA DEM Haritası:** 80m/piksel çözünürlüklü gerçek Güney Kutbu topografyası üzerinde hazır görev bölgelerini (Shackleton Rim, Nobile Rim 1, Mons Mouton, Malapert Massif vb.) veya **harita üzerinde tıklanan herhangi bir özel koordinatı (Lat/Lon)** analiz eder.
- **360° Krater Ufku & Astronot Görünümü:** İniş aracının gözünden veya yörünge kamerasından Güneş'in ve Dünya'nın krater dağları arkasında doğuşunu/batışını, yüzey sıcaklığını, güneş paneli üretimini (kW) ve Dünya lazer telemetri hattını gerçek zamanlı canlandırır.

### 2. 📈 Saatlik Enerji, İletişim ve Görev Modu Takvimi
- Görev süresince (7, 14 veya 28 Dünya günü) her bir saati **Tam Operasyon (Mavi)**, **Kısmi Operasyon (Turuncu)** ve **Kritik Kesinti / Uyku Modu (Kırmızı)** olarak sınıflandırır.
- Güneş yükselme açısını (°), o yöndeki gerçek krater ufuk engeli açısıyla (°) karşılaştırır. Grafikteki herhangi bir saate tıklandığında 3B simülasyon anında o saate gider.

### 3. ⚖️ A vs. B Yan Yana Karşılaştırma Matrisi
- İki farklı iniş bölgesini veya iki farklı fırlatma tarihini **0–100 Uygunluk Puanı (GO / CAUTION / NO-GO)**, aydınlanma süresi, maksimum karanlık, DTE iletişim yüzdesi (~1.28 sn ışık hızı gecikmesi) ve su buzu erişimi açısından yan yana yarıştırır.

### 4. 🤖 LUNA — Yapay Zeka Görev Analisti (Google Gemini API)
- Simülasyon verilerini okuyarak 5 maddelik teknik görev brifingi üretir ve kullanıcının sorduğu soruları (*"Neden B seçeneği daha güvenli?"*, *"Hangi bölgede Dünya iletişimi daha iyi?"*) gerçek sayısal telemetri verilerine dayanarak yanıtlar.

---

## 🛰️ Kullanılan NASA Verileri (NASA Data Sources)

1. **NASA PDS Geosciences Node — LRO LOLA GDR (`ldem_80s_80m.img`):** Ay Güney Kutbu (-80°S ile -90°S arası) 80 metre/piksel çözünürlüklü Sayısal Yükseklik Modeli (DEM), rakım, eğim ve 360° ufuk profili verileri.
2. **NASA JPL Horizons Ephemeris System:** Ay yüzeyindeki seçili koordinata göre Güneş ve Dünya'nın zamana bağlı görünür Azimut (Az) ve Yükseklik (El) açıları ile ışık zamanı (OWLT) verileri.
3. **NASA Artemis III & CLPS Aday İniş Bölgeleri:** Shackleton Rim, Connecting Ridge, Peak Near Shackleton, Nobile Rim 1, Haworth, Faustini Rim A, Mons Mouton ve De Gerlache koordinatları.

---

## 🛠️ Kurulum ve Yerelde Çalıştırma (Local Installation)

Projeyi kendi bilgisayarınızda çalıştırmak için aşağıdaki adımları izleyebilirsiniz:

### 1. Gereksinimler (Prerequisites)
- **Python 3.10+** ve **Git**

### 2. Depoyu İndirin ve Kütüphaneleri Kurun
```bash
git clone https://github.com/Ferhat-01/lunar-landing-site-navigator-3d1.git
cd lunar-landing-site-navigator-3d1
pip install fastapi uvicorn pydantic numpy pandas astropy astroquery
```

### 3. (İsteğe Bağlı) Gemini API Anahtarını Tanımlayın
LUNA AI soru-cevap asistanının canlı Gemini modeliyle çalışması için proje ana dizininde `.env` dosyası oluşturabilirsiniz *(anahtar girilmezse yerleşik LUNA Karar Motoru devreye girer)*:
```env
GEMINI_API_KEY=sizin_api_anahtariniz
```

### 4. Uygulamayı Başlatın (Run Application)
- **Windows'ta Tek Tıkla Başlatma:** Klasör içindeki **`PROJEYI_BASLAT.bat`** dosyasına çift tıklayın.
- **Terminalden Başlatma:**
```bash
python -m uvicorn app:app --reload --port 8000
```
Tarayıcınızda **`http://localhost:8000`** adresini açın.

---

## 📁 Proje Dosya Yapısı (Project Structure)

- `app.py` — FastAPI sunucusu, REST API uç noktaları (`/api/sites`, `/api/terrain3d`, `/api/analyze`, `/api/compare`, `/api/ai-comment`) ve LUNA AI entegrasyonu.
- `mission_analyzer.py` — NASA LOLA DEM arazi analizi, 360° krater ufuk gölgeleme (ray-casting) ve görev uygunluk puanlama (0-100) motoru.
- `nasa_ephemeris.py` — NASA JPL Horizons API üzerinden Güneş ve Dünya azimut/yükseklik vektör hesaplayıcısı.
- `nasa_lola_terrain.json` — Ön işlenmiş gerçek NASA LOLA Güney Kutbu 3B topografya matrisi ve aday bölge ufuk profilleri.
- `fetch_real_lola.py` — NASA PDS arşivinden ham `ldem_80s_80m.img` ikili (binary) verisini indirip işleyen veri hazırlama betiği.
- `static/index.html` — Three.js (WebGL) ve Plotly.js tabanlı 4 ekranlı etkileşimli Görev Kontrol Merkezi arayüzü.
- `PROJE_DOKUMANTASYONU_VE_PARAMETRELER.txt` — Tüm mühendislik parametrelerinin ve veri kaynaklarının detaylı teknik kılavuzu.

---

## 👥 Takım: ULUNOVA (Team UluNova)
**NASA Space Apps Challenge 2026**  
*Ay keşiflerinde riskleri önceden görmek ve bilimsel verilerle en güvenli iniş noktasını seçmek için geliştirilmiştir.* 🚀
