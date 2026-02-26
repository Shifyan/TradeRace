# 🚀 TradeRace - Autonomous AI Trading Agent

**TradeRace** adalah agen cerdas berbasis AI yang dirancang untuk melakukan pemindaian pasar secara mandiri. Proyek ini menggabungkan data presisi dari **Polygon.io** dengan kemampuan penalaran (_reasoning_) dari **Google Gemini 2.0 Flash** untuk memberikan analisis trading yang objektif.

Sistem ini bekerja secara otomatis menggunakan jadwal (_scheduler_) untuk memantau harga, menganalisis sentimen, dan mengirimkan sinyal trading langsung ke perangkat Anda.

---

## 🛠️ Tech Stack

- **Language:** Python 3.12+
- **Framework:** [FastAPI](https://fastapi.tiangolo.com/) (Backend & API Triggers)
- **Intelligence:** [Google GenAI SDK](https://github.com/google/generative-ai-python) (Gemini 2.0 Flash)
- **Database:** [Supabase](https://supabase.com/) (PostgreSQL) untuk State Management & Logs
- **Scheduler:** [APScheduler](https://apscheduler.readthedocs.io/) (Scheduled Tasks)
- **Market Data:** [Polygon.io](https://polygon.io/) API
- **Notifications:** [Ntfy.sh](https://ntfy.sh/) / Telegram

---

## 📁 Project Structure

```text
TradeRace/
├── app/
│   ├── agents/          # Prompt Engineering & Gemini Logic
│   ├── services/        # API Clients (Polygon, Gemini, Ntfy)
│   ├── database/        # Supabase CRUD & Connection
│   └── main.py          # FastAPI Entry Point & Scheduler Setup
├── .env                 # API Keys & Secrets (Private)
├── Dockerfile           # Production Container Configuration
├── requirements.txt     # Project Dependencies
└── README.md            # Documentation
```
