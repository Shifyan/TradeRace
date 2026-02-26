import datetime
import time
from app.services.polygon_client import fetch_daily_aggregates
from app.services.gemini_agent import analyze_stock_data, get_top_tickers_by_sentiment
from app.services.notification import send_ntfy_notification
from app.database.supabase_client import is_already_recommended, save_recommendation
from app.utils.logger import get_logger

logger = get_logger(__name__)

def scan_stocks_job():
    """Job to scan news for top 10 tickers, analyze their technicals, and send top 5 notifications."""
    logger.info("Starting stock scan job with AI Macro-Sentiment Analysis...")
    
    # 1. Ask Gemini to search Google News and pick top 10 tickers
    target_tickers = get_top_tickers_by_sentiment()
    if not target_tickers:
        logger.error("Failed to retrieve top tickers from AI. Aborting scan job.")
        return
        
    logger.info(f"Target Tickers for technical analysis: {target_tickers}")
    
    # Get dates for trend analysis (e.g., last 30 days)
    end_date_obj = datetime.date.today()
    start_date_obj = end_date_obj - datetime.timedelta(days=30)
    
    end_date_str = end_date_obj.strftime("%Y-%m-%d")
    start_date_str = start_date_obj.strftime("%Y-%m-%d")
    
    potential_picks = []
    
    # 2. Extract technicals and run AI analysis on the 10 tickers
    for ticker in target_tickers:
        try:
            logger.info(f"Processing technicals for ticker: {ticker}")
            
            # Anti-spam logic: Skip if already recommended today
            if is_already_recommended(ticker, end_date_str):
                logger.info(f"Already recommended {ticker} today ({end_date_str}), skipping...")
                continue
                
            data = fetch_daily_aggregates(ticker, start_date_str, end_date_str)
            if not data:
                logger.warning(f"No data found for {ticker} between {start_date_str} and {end_date_str}. Skipping analysis.")
                continue
                
            analysis = analyze_stock_data(ticker, data)
            if not analysis:
                logger.warning(f"Failed to analyze data for {ticker}. Skipping notification.")
                continue
                
            if analysis.get("recommendation") == "BUY" and analysis.get("confidence", 0) > 75:
                # Store potential pick for ranking
                potential_picks.append(analysis)
                logger.info(f"{ticker} passed technical BUY criteria with {analysis.get('confidence')}% confidence.")
            else:
                logger.info(f"Ticker {ticker} did not meet strong BUY criteria. Recommendation: {analysis.get('recommendation')}")
                
        except Exception as e:
            logger.error(f"Unexpected error processing ticker {ticker}: {e}", exc_info=True)
            
        # Add a delay to respect Gemini Free Tier Rate Limits (15 requests per minute)
        logger.info(f"Sleeping for 6 seconds to respect AI API Rate Limits...")
        time.sleep(6)
            
    # 3. Rank and Filter to Top 5
    if not potential_picks:
        logger.info("No strong technical BUY candidates found among the top news picks today.")
        return
        
    # Sort potentials by confidence (highest first)
    potential_picks.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    
    # Slice to top 5 maximum
    top_5_picks = potential_picks[:5]
    logger.info(f"Narrowed down to Top {len(top_5_picks)} picks based on highest technical confidence.")
    
    # 4. Blast Notifications
    for analysis in top_5_picks:
        ticker = analysis.get("ticker", "UNKNOWN")
        reasoning = analysis.get("reasoning", "Sinyal beli yang kuat terdeteksi.")
        entry_price = analysis.get("entry_price", "-")
        target_price = analysis.get("target_price", "-")
        stop_loss = analysis.get("stop_loss", "-")
        est_days = analysis.get("estimated_days_to_target", "-")
        
        message = f"Ticker: {ticker} (BUY)\n"
        message += f"Confidence: {analysis.get('confidence')}%\n"
        message += f"Entry: ${entry_price}\n"
        message += f"Target: ${target_price} ({est_days} Hari)\n"
        message += f"Stop Loss: ${stop_loss}\n\n"
        message += f"Analisa: {reasoning}"
        
        # Send notification via Ntfy.sh
        if send_ntfy_notification(f"BUY Alert: {ticker}", message):
            # Save to database to prevent duplicate notifications
            save_recommendation(ticker, end_date_str, analysis)
            logger.info(f"Successfully sent notification and saved to DB for {ticker}")
        else:
            logger.error(f"Failed to send notification for {ticker}. Not saving to database so it can be retried.")
            
    logger.info("Stock scan job completed.")
