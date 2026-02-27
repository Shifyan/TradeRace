# Dokumentasi Teknis & Alur Bisnis StockRace

Aplikasi **StockRace** adalah sistem analitik saham yang sangat canggih dan sepenuhnya otomatis. Sistem ini menggabungkan pencarian isu global _(Macro Economy)_ menggunakan kecerdasan buatan, dengan lapisan pertahanan Analisa Teknikal yang dibantu oleh perhitungan matematika murni untuk menghasilkan panduan _Risk/Reward_ terbaik bagi Anda.

---

## 🏗️ Arsitektur Sistem Baru

### 1. The Brain: Google Gemini 2.5 Flash & 2.0 Flash (Auto-Fallback)

- **Fungsi Utama**: AI bertindak sebagai otak yang mengolah data sentimen dan teknikal.
- **Quota Protection (Auto-Fallback)**: Karena menggunakan API _Free Tier_, batas harian rentan tersentuh (Error 429). Jika model utama `gemini-2.5-flash` menolak bekerja karena limit, _script_ akan langsung menangkap _error_ secara diam-diam dan menembak ulang permintaan ke model cadangan `gemini-2.0-flash`. Sistem tidak akan pernah berhenti bekerja hanya karena masalah kuota.

### 2. The Data: Polygon.io

- **Fungsi Utama**: Menyediakan harga penutupan dan data indikator matematika murni (SMA, EMA, MACD, RSI).
- **Rate Limit Protection**: Untuk menghormati limit tier gratis maksimum 5 panggilan/menit, fungsi analisis dipasang _jeda tidur_ `time.sleep(12)` setiap kali menembak data indikator baru. Alur akan terasa lambat (disengaja) tapi sangat stabil.

### 3. The Endpoints (`app/main.py`)

- **Automated Cron**: Berjalan setiap pukul 19:30 WIB di hari kerja (Senin-Jumat).
- **On-Demand technical**: Endpoint `/api/analyze/{ticker}` yang disediakan khusus jika user ingin memeriksa saham tertentu secara kilat di luar jam pantauan.
- **Testing**: Endpoint `/api/test-notify` untuk debug notifikasi tanpa menyedot limit API.

---

## 🔀 Alur Kerja Utama (Cron Job Flow)

Alur otomatis yang akan berjalan setiap hari ini memiliki 4 tahap ketat:

### Tahap 1: Macro Economist (Grounding Search)

Gemini ditugaskan menjadi **Ekonom Makro**. Ia dibekali fitur _Google Search Grounding_ untuk berselancar di internet mencari momentum politik, suku bunga, dan isu global terbaru hari ini.

- **Rule 1**: AI diwajibkan mengabaikan saham yang akan merilis Laporan Laba (_Earnings_) dalam jeda 2 hari ke depan untuk menghindari malapetaka volatilitas.
- **Output**: Menghasilkan **Top 10 Ticker** yang mendapat sentimen/katalis paling positif hari ini.

### Tahap 2: Technical Analyst (Risk/Reward Scan)

Ke-10 daftar saham "jalur langit" tersebut kemudian diturunkan ke fungsi teknikal. AI berganti peran menjadi **Senior Technical Analyst** dengan menyerap grafik historis 200 hari.

- **Rule 2**: AI wajib menghitung potensi kerugian dan keuntungan (_Risk/Reward_). Jika keuntungan terprediksi `(Target - Entry)` dibanding risiko loss `(Entry - Stop Loss)` rasionya lebih buruk dari **1:2**, AI dilarang keras merekomendasikan `"BUY"`. Statusnya harus diturunkan menjadi `"HOLD"` atau `"NEUTRAL"`.

### Tahap 3: Python Emergency Brake (Mathematical Filter)

Setelah AI setuju memberikan rekomendasi `BUY`, aplikasi backend Python (bukan AI) melakukan pengecekan ulang secara matematis sebagai _"Rem Darurat"_.

- **Logic**: `reward = target_price - entry_price` dan `risk = entry_price - stop_loss`.
- **Validation**: Jika secara matematika Python menemukan `reward < (2 * risk)`, saham tersebut langsung **dibuang** dari daftar meskipun AI bersikeras merekomendasikannya. Hanya profil sehat yang lolos.

### Tahap 4: The Final 5 & Ntfy Push

Dari serangkaian penyaringan berat tersebut, mungkin hanya akan tersisa sedikit saham.
Sistem mengurutkan sisanya berdasarkan tingkat keyakinan (Confidence) > 75%, dan mengambil maksimal **Top 5**.
Pesan peringkas berisi _R/R Ratio_, Target Hari, Label, dll. kemudian dikemas menggunakan _Encoding ASCII_ untuk menghindari _crash logger_ di Windows, dan didorong seketika ke _handphone_ Anda melalui Ntfy.

---

## 🛠️ Alur Endpoint Khusus: `/api/analyze/{ticker}`

Ini adalah alur alternatif untuk mengecek ticker manual.
Berbeda dengan sistem _Cron Job_ di atas yang berbasis Berita/Makro, endpoint ini adalah alat ukur **100% Teknikal Murni** tanpa fitur pencarian Google (No Grounding).

1. Menarik 5 pergerakan terakhir dari indikator **SMA-200, EMA-20, MACD, dan RSI**.
2. Memberikan instruksi mesin (Rule-based) ekstrem pada AI:
   - **Filter Utama**: Tolak mentah-mentah jika Harga Penutupan Saat Ini berada **di bawah SMA-200** (Long-term downtrend).
   - Momentum MACD menyilang (_Crossover_ signal).
   - Zona RSI menguntungkan (Bukan _overbought_ >70).
3. Mengembalikan penilaian instan ke layar pengguna lengkap dengan ringkasan analisa teknikalnya agar mereka tahu area mana yang sedang dilewati saham tersebut.
