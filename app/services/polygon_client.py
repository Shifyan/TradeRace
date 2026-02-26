import requests
from typing import Dict, Any, Optional
from app.config import settings

def fetch_daily_aggregates(ticker: str, date: str) -> Optional[Dict[str, Any]]:
    """
    Fetch daily aggregated data from Polygon.io for a specific ticker.
    Date format: YYYY-MM-DD
    """
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{date}/{date}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "apiKey": settings.POLYGON_API_KEY
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        if data.get("resultsCount", 0) > 0:
            return data["results"][0]
    return None
