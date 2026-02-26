# StockRace: Automated Stock Recommendation System

StockRace adalah server backend berbasis Python yang mengotomatisasi pemindaian saham menggunakan data dari Polygon.io, dianalisis menggunakan kecerdasan buatan Gemini API, dan mengirimkan rekomendasi "BUY" yang kuat melalui notifikasi Ntfy.sh dan Telegram.

## 🚀 Fitur Utama

- **On-Demand Trigger**: Endpoint API untuk memicu pemindaian saham kapan saja via Webhook.
- **Automated Scheduler**: Menjalankan pemindaian otomatis setiap jam pada hari kerja (Senin-Jumat) menggunakan APScheduler.
- **AI Analysis**: Integrasi dengan Google Gemini 1.5 (SDK terbaru `google-genai`) untuk analisis sentimen dan teknikal dalam format JSON.
- **Deduplication Logic**: Menyimpan riwayat rekomendasi di Supabase (PostgreSQL) untuk mencegah notifikasi ganda pada hari yang sama.
- **Instant Notification**: Mengirimkan alert ke Ntfy.sh yang dapat diteruskan ke Telegram/Mobile.

## 🛠️ Tech Stack

- **Framework**: FastAPI
- **Scheduler**: APScheduler
- **Database**: Supabase (supabase-py)
- **AI Engine**: Google GenAI (Gemini 1.5 Flash)
- **Data Source**: Polygon.io Daily Aggregates
- **Deployment**: Docker & Docker Compose

## 📁 Struktur Folder

```text
app/
├── database/       # Logic koneksi Supabase & manajemen data
├── services/       # Integrasi API Eksternal (Polygon, Gemini, Ntfy)
├── tasks/          # Background jobs & stock scanning logic
├── config.py       # Manajemen environment variables (Pydantic Settings)
└── main.py         # Entry point FastAPI & Scheduler setup
```

## ⚙️ Persiapan (Setup)

### 1. Prasyarat

- Python 3.11+
- Akun Polygon.io (API Key)
- Akun Google AI Studio (Gemini API Key)
- Proyek Supabase (URL & Service Role Key)

### 2. Konfigurasi Environment

Salin file `.env.example` menjadi `.env` dan isi kredensial Anda:

```bash
cp .env.example .env
```

### 3. Instalasi Lokal

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 4. Menjalankan via Docker

```bash
docker build -t stockrace-app .
docker run -p 8000:8000 --env-file .env stockrace-app
```

## 📡 API Endpoints

- `GET /`: Cek status server.
- `POST /api/scan/trigger`: Memicu pemindaian saham secara manual di background.

## 📝 Catatan Penting

- Pemindai otomatis berjalan sesuai interval di `app/main.py` menggunakan CronTrigger.
- Daftar ticker saham yang dipantau dapat diubah di `app/tasks/stock_scanner.py` pada variabel `TARGET_TICKERS`.

---

_Developed by Shifyan Almustafid._
