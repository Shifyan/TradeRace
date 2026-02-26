import datetime
from app.services.polygon_client import fetch_daily_aggregates
from app.services.gemini_agent import analyze_stock_data
from app.services.notification import send_ntfy_notification
from app.database.supabase_client import is_already_recommended, save_recommendation

# List of tickers to scan (Add or remove as needed)
TARGET_TICKERS = ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"]

def scan_stocks_job():
    """Job to scan stocks, analyze them, and send notifications."""
    print("Starting stock scan job...")
    
    # Get today's date formatted as YYYY-MM-DD
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    
    for ticker in TARGET_TICKERS:
        if is_already_recommended(ticker, today_str):
            print(f"Already processed {ticker} for {today_str}, skipping...")
            continue
            
        data = fetch_daily_aggregates(ticker, today_str)
        if not data:
            print(f"No data found for {ticker} on {today_str}.")
            continue
            
        analysis = analyze_stock_data(ticker, data)
        if not analysis:
            continue
            
        if analysis.get("recommendation") == "BUY" and analysis.get("confidence", 0) > 75:
            reasoning = analysis.get("reasoning", "Strong buy signals detected.")
            message = f"Ticker: {ticker}\nConfidence: {analysis.get('confidence')}%\nReason: {reasoning}"
            
            # Send notification via Ntfy.sh
            send_ntfy_notification(f"BUY Alert: {ticker}", message)
            
            # Save to database to prevent duplicate notifications
            save_recommendation(ticker, today_str, analysis)
            print(f"Sent recommendation for {ticker}")
            
    print("Stock scan job completed.")
