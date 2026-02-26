from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.tasks.stock_scanner import scan_stocks_job

scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup event: configure and start APScheduler
    # Will run every hour from Monday to Friday
    trigger = CronTrigger(day_of_week="mon-fri", hour="19", minute="30")
    scheduler.add_job(
        scan_stocks_job, 
        trigger=trigger, 
        id="scan_stocks_job", 
        replace_existing=True
    )
    scheduler.start()
    
    yield
    
    # Shutdown event: gracefully shutdown APScheduler
    scheduler.shutdown()

app = FastAPI(
    title="Stock Recommendation API", 
    description="Automated stock scanning and recommendation using Polygon and Gemini",
    lifespan=lifespan
)

@app.get("/")
def read_root():
    return {"status": "Automated Stock Recommendation Server is running"}

@app.post("/api/scan/trigger")
def trigger_scan_on_demand(background_tasks: BackgroundTasks):
    """Webhook endpoint to manually trigger a stock scan on demand."""
    background_tasks.add_task(scan_stocks_job)
    return {"message": "Stock scan triggered in the background"}
