# StockRace: Automated Stock Recommendation System

StockRace adalah server backend berbasis Python yang mengotomatisasi pemindaian saham menggunakan data dari Polygon.io, dianalisis menggunakan kecerdasan buatan Gemini API (Google GenAI), dan mengirimkan rekomendasi "BUY" yang cerdas melalui push notifikasi Ntfy.sh.

## 🚀 Fitur Utama

- **Two-Stage AI Analysis**:
  1. **Ekonom Makro (Grounding)**: Mencari 10 ticker potensial berdasarkan berita global terbaru menggunakan Google Search Grounding.
  2. **Senior Technical Analyst**: Menganalisa 10 ticker tersebut secara mendalam menggunakan data teknikal untuk memilih Top 5 rekomendasi terbaik.
- **Risk Management System**:
  - **Risk/Reward Filter (AI)**: AI diinstruksikan hanya memberikan sinyal "BUY" jika potensi Reward minimal 2x dari Risk (1:2).
  - **Mathematical Emergency Brake**: Validasi backend Python untuk memastikan `(target - entry) >= 2 * (entry - stop_loss)`.
  - **SMA 200 Barrier**: Menghindari pembelian saham yang berada di bawah Moving Average 200 hari.
- **On-Demand Risk Analysis**: Endpoint khusus untuk melakukan cek teknikal instan pada ticker tertentu (SMA 200, EMA 20, MACD, RSI).
- **Automated Fallback**: Otomatis beralih dari Gemini 2.5 Flash ke Gemini 2.0 Flash jika terkena limit quota (429 Resource Exhausted).
- **Free Tier Optimized**: Dilengkapi dengan jeda (sleep timer) otomatis untuk mematuhi limit Polygon (5 req/min) dan Gemini API Free Tier.
- **Deduplication**: Integrasi Supabase untuk mencegah spam notifikasi yang sama di hari yang sama.

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **Scheduler**: APScheduler (Cron harian 19:30 WIB Senin-Jumat)
- **Database**: Supabase (PostgreSQL)
- **AI Engine**: Google GenAI (Gemini 2.5/2.0 Flash)
- **Data Source**: Polygon.io (Daily Aggregates & Technical Indicators)
- **Notification**: Ntfy.sh (Push ke Android/iOS/Web)

## 📁 Struktur Folder

```text
app/
├── services/       # Integrasi API (Polygon Indicators, Gemini Grounding, Ntfy)
├── tasks/          # Background jobs (Sentiment Search -> Tech Analysis Flow)
├── utils/          # Logger & Helper
├── config.py       # Pydantic Settings
└── main.py         # Entry point FastAPI & Endpoints
```

## ⚙️ Persiapan (Setup)

### 1. Prasyarat

- Python 3.11+
- API Key: Polygon.io, Google AI Studio, Supabase URL & Service Key.

### 2. Konfigurasi Environment

Salin file `.env.example` menjadi `.env` dan isi kredensial Anda:

```bash
cp .env.example .env
```

### 3. Instalasi Lokal

Jika Anda ingin menjalankan server langsung di komputer Anda:

```bash
# Buat virtual environment (opsional)
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate # Linux/Mac

# Install library yang dibutuhkan
pip install -r requirements.txt

# Jalankan server
uvicorn app.main:app --reload
```

### 4. Menjalankan via Docker

Jika server ingin di-deploy ke VPS atau berjalan terisolasi:

```bash
# Build image Docker
docker build -t stockrace-app .

# Jalankan container
docker run -p 8000:8000 --env-file .env stockrace-app
```

## 📡 API Endpoints

- `GET /`: Status server.
- `POST /api/scan/trigger`: Menjalankan alur pemindaian harian (Macro Sentiment -> Tech Analysis) secara manual.
- `GET /api/analyze/{ticker}`: Analisa teknikal instan (SMA200, EMA20, MACD, RSI) untuk ticker tertentu.
- `GET /api/test-notify`: Mengirim notifikasi tes format ke aplikasi Ntfy.

## 📝 Business Logic Rules

- **Earnings Protection**: AI secara otomatis mengabaikan saham yang akan merilis laporan laba (Earnings) dalam 2 hari ke depan.
- **Indonesian Reasoning**: Semua penjelasan analisa dari AI (reasoning) disajikan dalam Bahasa Indonesia yang ringkas.
- **Model Fallback**: Jika Flash 2.5 mencapai limit harian, sistem otomatis menggunakan Flash 2.0.

---

_Developed by Shifyan._
