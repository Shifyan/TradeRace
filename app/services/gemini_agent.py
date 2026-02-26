import json
from google import genai
from google.genai import types
from typing import Dict, Any, Optional, List
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
except Exception as e:
    logger.error(f"Failed to initialize Gemini Client: {e}")
    client = None

def get_top_tickers_by_sentiment() -> List[str]:
    """
    Act as a Macro Economist. Uses Google Search Grounding to find the latest
    economic, political, and market news to determine the top 10 potential tickers.
    """
    if not client:
        logger.error("Gemini client is not initialized. Cannot get top tickers.")
        return []
        
    prompt = """
    Cari berita terbaru hari ini terkait ekonomi makro Amerika Serikat dan Global, kebijakan politik, 
    dan sentimen pasar saham secara real-time menggunakan Google Search. 
    
    Analisa berita tersebut dan pilih MAKSIMAL 10 saham (Ticker Symbol) AS yang paling sangat berpotensi 
    naik dalam waktu dekat berdasarkan sentimen faktual hari ini.
    
    Abaikan saham yang sentimennya negatif atau netral. Fokus pada yang mendapat katalis positif terkuat.
    
    KEMBALIKAN HANYA ARRAY JSON LIST OF STRINGS (kode Ticker saja) TANPA TEKS LAIN ATAU PENJELASAN APAPUN. Contoh:
    ["AAPL", "TSLA", "NVDA", "PLTR"]
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{'google_search': {}}] # Enable Google Search Grounding
            )
        )
        
        # Log the raw response for debugging in case of failure
        raw_text = response.text.strip() if response.text else ""
        logger.debug(f"Raw Gemini Grounding Response: {raw_text}")
        
        if not raw_text:
            logger.error("Gemini returned an empty response for top tickers.")
            return []

        # Robust cleaning of the response text (handling markdown and potential prefix/suffix)
        processed_text = raw_text
        if "```json" in processed_text:
            processed_text = processed_text.split("```json")[1].split("```")[0].strip()
        elif "```" in processed_text:
            processed_text = processed_text.split("```")[1].split("```")[0].strip()
        
        # Remove common characters that might be outside the JSON array
        processed_text = processed_text.strip()
        
        # Try to find the start and end of a JSON array if cleaning failed
        if not (processed_text.startswith("[") and processed_text.endswith("]")):
            start_idx = processed_text.find("[")
            end_idx = processed_text.rfind("]")
            if start_idx != -1 and end_idx != -1:
                processed_text = processed_text[start_idx:end_idx+1]
            
        tickers = json.loads(processed_text)
        if isinstance(tickers, list):
            # Limit to exactly 10 if AI somehow ignores the prompt
            limited_tickers = [str(t).upper().strip() for t in tickers[:10]]
            logger.info(f"AI Selected Top Tickers based on Macro News: {limited_tickers}")
            return limited_tickers
        else:
            logger.error(f"AI returned invalid format (not a list) for top tickers: {type(tickers)}")
            return []
            
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response from Gemini Grounding: {e}. Raw content was: {raw_text[:200]}...")
        return []
    except Exception as e:
        logger.error(f"Error fetching top tickers via Gemini Grounding: {e}")
        return []

def analyze_stock_data(ticker: str, data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Analyze historical technical data using Gemini and return JSON representation."""
    if not client:
        logger.error("Gemini client is not initialized. Cannot analyze data.")
        return None
        
    # Extract only essential data to save tokens (e.g., closing prices and volume)
    simplified_data = [{"c": d.get("c"), "v": d.get("v"), "t": d.get("t")} for d in data]
        
    prompt = f"""
    Analyze the following historical daily aggregate stock data for {ticker} over the last time period.
    The data is an array of records where 'c' is the closing price, 'v' is the trading volume, and 't' is the unix timestamp.
    
    Data:
    {json.dumps(simplified_data)}
    
    Act as a Senior Financial Analyst focusing on technical analysis. 
    Analyze the trend, momentum, and volume of the closing prices.
    Determine if this stock is a good BUY right now.
    
    Respond strictly in JSON format with the following schema:
    {{
        "ticker": "{ticker}",
        "recommendation": "BUY" | "HOLD" | "SELL",
        "confidence": <float 0.0 - 100.0>,
        "entry_price": <float recommended entry price>,
        "target_price": <float take profit target>,
        "stop_loss": <float cut loss limit>,
        "estimated_days_to_target": <integer estimation of days to reach target frame>,
        "reasoning": "<short explanation based on the closing price trend and volume. MUST BE WRITTEN IN INDONESIAN LANGUAGE (BAHASA INDONESIA)>"
    }}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        # Model is configured to return JSON application/json
        result = json.loads(response.text)
        logger.info(f"Successfully analyzed {ticker}. Recommendation: {result.get('recommendation')}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response from Gemini for {ticker}: {e}\nRaw Response: {response.text}")
    except Exception as e:
        logger.error(f"Error analyzing data with Gemini for {ticker}: {e}")
        
    return None
