from supabase import create_client, Client
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

def get_supabase_client() -> Client:
    try:
        return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        raise

def is_already_recommended(ticker: str, date: str) -> bool:
    """Check if the ticker was already recommended on a specific date."""
    try:
        supabase = get_supabase_client()
        response = supabase.table("recommendations").select("id").eq("ticker", ticker).eq("date", date).execute()
        return len(response.data) > 0
    except Exception as e:
        logger.error(f"Database error checking recommendation for {ticker} on {date}: {e}")
        # Return True on error to prevent spamming notifications if DB is down
        return True 

def save_recommendation(ticker: str, date: str, analysis: dict) -> None:
    """Save the recommendation to prevent duplicate notifications."""
    try:
        supabase = get_supabase_client()
        supabase.table("recommendations").insert({
            "ticker": ticker,
            "date": date,
            "analysis": analysis
        }).execute()
        logger.info(f"Saved recommendation for {ticker} to database.")
    except Exception as e:
        logger.error(f"Database error saving recommendation for {ticker}: {e}")
