from supabase import create_client, Client
from app.config import settings

def get_supabase_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

def is_already_recommended(ticker: str, date: str) -> bool:
    """Check if the ticker was already recommended on a specific date."""
    supabase = get_supabase_client()
    response = supabase.table("recommendations").select("id").eq("ticker", ticker).eq("date", date).execute()
    return len(response.data) > 0

def save_recommendation(ticker: str, date: str, analysis: dict) -> None:
    """Save the recommendation to prevent duplicate notifications."""
    supabase = get_supabase_client()
    supabase.table("recommendations").insert({
        "ticker": ticker,
        "date": date,
        "analysis": analysis
    }).execute()
