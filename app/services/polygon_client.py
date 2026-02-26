import requests
from typing import Dict, Any, Optional, List
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

def fetch_daily_aggregates(ticker: str, start_date: str, end_date: str) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch daily aggregated data from Polygon.io for a specific ticker over a date range.
    Date format: YYYY-MM-DD
    """
    url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}"
    params = {
        "adjusted": "true",
        "sort": "asc",
        "limit": 120, # Added limit as per user example
        "apiKey": settings.POLYGON_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        data = response.json()
        if data.get("resultsCount", 0) > 0:
            return data["results"]
        else:
            logger.warning(f"No results found for {ticker} between {start_date} and {end_date}")
            return None
            
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error fetching data for {ticker}: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching data for {ticker}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in Polygon client for {ticker}: {e}")
        
    return None
