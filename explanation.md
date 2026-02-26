# Dokumentasi Teknis & Alur Bisnis StockRace

Aplikasi **StockRace** adalah sistem rekomendasi saham otomatis yang menggabungkan analitik berita makro ekonomi (Sentiment Analysis) dengan analisa pergerakan harga historis (Technical Analysis) menggunakan AI tercanggih Google Gemini dan data pasar Polygon.io.

---

## 🏗️ Arsitektur & Arsitektur Kode

### 1. Entry Point & Scheduler (`app/main.py`)

- **Fungsi**: Titik masuk aplikasi berbasis FastAPI.
- **Logic**: Menginisialisasi `APScheduler` saat aplikasi dimulai (`lifespan`). Scheduler ini diatur untuk menjalankan `scan_stocks_job` setiap jam pada hari kerja (Senin-Jumat). Juga menyediakan endpoint `POST /api/scan/trigger` untuk memicu pemindaian secara manual via webhook.

### 2. Macro Sentiment Agent (`app/services/gemini_agent.py` -> `get_top_tickers_by_sentiment`)

- **Fungsi**: Bertindak sebagai Ekonom Makro.
- **Logic**: Menggunakan Gemini 2.5 Flash dengan fitur **Google Search Grounding**. AI akan mencari berita terbaru (politik, ekonomi, inflasi, laporan laba) secara real-time di internet.
- **Output**: Memilih maksimal **10 Ticker Saham** yang memiliki sentimen positif terkuat hari ini.

### 3. Data Acquisiton (`app/services/polygon_client.py`)

- **Fungsi**: Penarik data harga riil.
- **Logic**: Mengambil data harian (OHLCV) dari Polygon.io untuk rentang **30 hari ke belakang** bagi setiap ticker yang dipilih oleh AI Macro. Data ini penting untuk melihat tren pergerakan harga.

### 4. Technical Analysis Agent (`app/services/gemini_agent.py` -> `analyze_stock_data`)

- **Fungsi**: Bertindak sebagai Senior Technical Analyst.
- **Logic**: Menerima data 30 hari dari Polygon. AI menganalisa pola harga penutupan (_closing price_), volume, dan momentum.
- **Output**: JSON berisi rekomendasi (BUY/HOLD/SELL), `entry_price`, `target_price`, `stop_loss`, dan alasan teknikal dalam Bahasa Indonesia.

### 5. Notification & Deduplication (`app/services/notification.py` & `app/database/supabase_client.py`)

- **Fungsi**: Pengirim informasi dan pengontrol duplikasi.
- **Logic**:
  - **Deduplication**: Mengecek Supabase apakah ticker tersebut sudah direkomendasikan hari ini. Jika sudah, proses dilewati untuk menghindari spam.
  - **Notification**: Mengirim push notification ke Ntfy.sh (yang bisa diteruskan ke Telegram/Mobile) jika hasil analisa teknikal memiliki status `BUY` dengan tingkat keyakinan (_confidence_) > 75%.

---

## 🔀 Alur Kerja Detail (Step-by-Step)

### Tahap 1: Pencarian Peluang (Macro Scan)

Sistem tidak menggunakan daftar saham yang kaku. Pertama, Gemini akan "membaca berita" dunia hari ini menggunakan Google Search. Jika ada berita bahwa sektor AI sedang naik atau kebijakan suku bunga menguntungkan sektor tertentu, Gemini akan memberikan daftar 10 perusahaan (misal: `NVDA`, `MSFT`, `AMD`, dll).

### Tahap 2: Validasi Harga (Technical Scan & Rate Limiting)

Aplikasi melakukan _looping_ terhadap 10 ticker tersebut.

1. **Delay**: Menggunakan `time.sleep(6)` di setiap iterasi saham untuk menghormati kuota gratis API Gemini (Rate Limit).
2. **Tarik Data**: Mengambil data harga 30 hari terakhir.
3. **Analisa AI**: Gemini menganalisa apakah tren harga mendukung berita makronya. Saham yang dianggap layak beli dimasukkan ke dalam daftar "Kandidat Potensial".

### Tahap 3: Penyaringan Puncak (The Final 5)

Dari 10 saham awal, mungkin tidak semuanya memiliki grafik teknikal yang bagus.

1. Semua kandidat yang berstatus `BUY` dikumpulkan dan diurutkan berdasarkan skor **Confidence** (keyakinan AI) tertinggi.
2. Aplikasi melakukan _filter_ ketat: Hanya **Top 5** saham dengan skor tertinggi yang akan lanjut ke tahap notifikasi.

### Tahap 4: Pengiriman & Pencatatan

1. Mengirim notifikasi detail (Entry, Target, Stop Loss, Alasan) ke user.
2. Mencatat ID ticker dan tanggal hari ini ke Supabase PostgreSQL. Dengan adanya catatan ini, jika aplikasi berjalan lagi 1 jam kemudian, sistem akan tahu bahwa saham ini sudah dikirim dan tidak akan mengirimnya ulang.

---

## 💡 Ringkasan Logika Bisnis

Aplikasi ini menjawab tantangan: _"Bagaimana cara menemukan saham yang secara berita bagus, secara grafik teknis juga mendukung, tetapi tidak membombardir user dengan terlalu banyak notifikasi?"_

Dengan alur **Dunia (News) -> Data (Polygon) -> Filter (Technical) -> Top 5 (Final)**, aplikasi memastikan user hanya mendapatkan informasi yang benar-benar berkualitas tinggi dan tervalidasi oleh dua metode analisa (Fundamental/Sentimen & Teknikal).
