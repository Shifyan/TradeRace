from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, HTTPException
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.tasks.stock_scanner import scan_stocks_job
import datetime
import time
from app.services.polygon_client import fetch_daily_aggregates, fetch_technical_indicator
from app.services.gemini_agent import analyze_ticker_with_indicators
from app.services.notification import send_ntfy_notification
from app.database.supabase_client import save_recommendation, get_supabase_client

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

@app.get("/api/analyze/{ticker}")
def analyze_ticker_on_demand(ticker: str):
    """
    On-demand analysis endpoint for a specific ticker.
    Fetches purely technical indicators and evaluates with Gemini.
    """
    ticker = ticker.upper()
    
    # We still need the current price, so fetch the latest aggregate
    end_date_obj = datetime.date.today()
    start_date_obj = end_date_obj - datetime.timedelta(days=10) # 10 days is enough to get latest close
    end_date_str = end_date_obj.strftime("%Y-%m-%d")
    start_date_str = start_date_obj.strftime("%Y-%m-%d")
    
    tech_data = fetch_daily_aggregates(ticker, start_date_str, end_date_str)
    if not tech_data:
        raise HTTPException(status_code=404, detail=f"No technical data found for ticker {ticker}")
        
    current_price = tech_data[-1].get("c", 0)
    
    # Fetch Indicators (with 12 second delays to respect Polygon Free Tier limit of 5 req/min)
    # The endpoint needs 5 API calls total (1 agg + 4 indicators) = ~1 minute to complete
    time.sleep(12)
    sma_20 = fetch_technical_indicator(ticker, "sma", {"window": 20}) or []
    
    time.sleep(12)
    ema_20 = fetch_technical_indicator(ticker, "ema", {"window": 20}) or []
    
    time.sleep(12)
    macd = fetch_technical_indicator(ticker, "macd", {"short_window": 8, "long_window": 17, "signal_window": 9}) or []
    
    time.sleep(12)
    rsi = fetch_technical_indicator(ticker, "rsi", {"window": 14}) or []
    
    # Analyze with Gemini
    try:
        analysis = analyze_ticker_with_indicators(ticker, current_price, sma_20, ema_20, macd, rsi)
        if not analysis:
            raise HTTPException(status_code=500, detail="Failed to analyze technicals with Gemini")
            
        # 4. Format and Send Notification
        recommendation = str(analysis.get("recommendation", "Neutral")).upper()
        summary = analysis.get("summary", "")
        key_risks = analysis.get("key_risks", "")
        
        # Format and Send Notification
        recommendation = str(analysis.get("recommendation", "Neutral")).upper()
        summary = analysis.get("summary", "")
        key_risks = analysis.get("key_risks", "")
        
        status_emoji = "🟢" if recommendation == "BULLISH" else "🔴" if recommendation == "BEARISH" else "🟡"
        
        message = f"Ticker: {ticker} {status_emoji} ({recommendation})\n\n"
        message += f"Summary:\n{summary}\n\n"
        message += f"Key Risks:\n{key_risks}"
        
        send_ntfy_notification(f"Risk Analysis: {ticker}", message)
        
        return {
            "status": "success",
            "message": f"Analysis completed for {ticker} and notification has been pushed to your device."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        if "429" in str(e):
             raise HTTPException(status_code=429, detail="AI Quota Exceeded (Resource Exhausted). Try again later.")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/api/test-notify")
def test_notification():
    """Endpoint specifically for testing the Ntfy notification formatting with Mock Data."""
    try:
        ticker = "MOCK"
        recommendation = "BULLISH"
        status_emoji = "🟢"
        summary = "Saham MOCK baru saja menembus resistensi kuat setelah memantul dari area SMA-200. Indikator MACD menunjukkan momentum akumulasi volume yang sangat agresif. RSI berada di level aman (55) menandakan masih ada ruang besar untuk reli naik lebih lanjut minggu ini."
        key_risks = "- Volatilitas sektor tech minggu ini cukup tinggi.\n- Waspadai jika penutupan harian kembali turun di bawah EMA-20."
        
        message = f"Ticker: {ticker} {status_emoji} ({recommendation})\n\n"
        message += f"Summary:\n{summary}\n\n"
        message += f"Key Risks:\n{key_risks}"
        
        title = f"Risk Analysis: {ticker}"
        
        success = send_ntfy_notification(title, message)
        
        if success:
            return {"status": "success", "message": "Mock notification sent successfully. Please check your Ntfy app."}
        else:
            raise HTTPException(status_code=500, detail="Failed to send mock notification.")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error testing notification: {str(e)}")

@app.post("/api/test-db/insert")
def test_db_insert():
    """Endpoint for testing database insertion - adds a 'MOCK' ticker entry."""
    try:
        today = datetime.date.today().strftime("%Y-%m-%d")
        mock_analysis = {
            "recommendation": "BULLISH",
            "confidence": 99.9,
            "reasoning": "Database testing mock entry."
        }
        save_recommendation("MOCK", today, mock_analysis)
        return {"status": "success", "message": f"Successfully inserted MOCK data for {today}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database insert test failed: {str(e)}")


@app.delete("/api/test-db/cleanup")
def test_db_cleanup():
    """Endpoint for testing database deletion - removes all 'MOCK' ticker entries."""
    try:
        supabase = get_supabase_client()
        response = supabase.table("recommendations").delete().eq("ticker", "MOCK").execute()
        return {
            "status": "success", 
            "message": f"Cleanup successful. Removed {len(response.data)} mock entries."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database cleanup failed: {str(e)}")
    
    
@app.get("/api/test-API/fetch")
def test_polygon_api():
    """Endpoint for testing Polygon API data fetching."""
    try:
        ticker = "AAPL"
        end_date_obj = datetime.date.today()
        start_date_obj = end_date_obj - datetime.timedelta(days=200)
        end_date_str = end_date_obj.strftime("%Y-%m-%d")
        start_date_str = start_date_obj.strftime("%Y-%m-%d")
        print(f"Testing Polygon API fetch for {ticker} from {start_date_str} to {end_date_str}...")
        data = fetch_daily_aggregates(ticker, start_date_str, end_date_str)
        current_price = data[-1].get("c", 0)

        if data:
            return {"status": "success", "data": data, "current_price": current_price}
        else:
            raise HTTPException(status_code=404, detail=f"No data found for {ticker} between {start_date_str} and {end_date_str}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing Polygon API: {str(e)}")
