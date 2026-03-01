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
    Bertindaklah sebagai Ekonom Makro. Cari berita terbaru hari ini terkait ekonomi makro Amerika Serikat dan Global, kebijakan politik, 
    dan sentimen pasar saham secara real-time menggunakan Google Search. 
    
    Analisa berita tersebut dan pilih MAKSIMAL 2 saham (Ticker Symbol) AS yang paling sangat berpotensi 
    naik dalam waktu dekat berdasarkan isu global terbaru dan sentimen faktual hari ini.
    
    PENTING: JANGAN pilih saham (ticker) yang memiliki jadwal laporan laba (Earnings) dalam 2 hari ke depan.
    Abaikan saham yang sentimennya negatif atau netral. Fokus pada yang mendapat katalis positif terkuat.
    
    KEMBALIKAN HANYA ARRAY JSON LIST OF STRINGS (kode Ticker saja) TANPA TEKS LAIN ATAU PENJELASAN APAPUN. Contoh:
    ["AAPL", "TSLA", "NVDA", "PLTR"]
    """
    
    try:
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[{'google_search': {}}] # Enable Google Search Grounding
                )
            )
        except Exception as inner_e:
            if "429" in str(inner_e):
                logger.warning("Rate limit reached for gemini-2.5-flash on sentiment analysis. Falling back to gemini-2.0-flash...")
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[{'google_search': {}}]
                    )
                )
            else:
                raise inner_e
        
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

def analyze_stock_data(ticker: str, data: List[Dict[str, Any]], sma_20, ema_20, macd, rsi) -> Optional[Dict[str, Any]]:
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

    Indicators:
    - SMA 20: {json.dumps(sma_20)}  (list of float values)
    - EMA 20: {json.dumps(ema_20)}  (list of float values)
    - MACD (8, 17, 9): {json.dumps(macd)}   (list of dicts with keys 'value', 'signal', 'histogram')
    - RSI (14): {json.dumps(rsi)}  (list of float values)
    
    Act as a Senior Technical Analyst. 
    Analyze the trend, momentum, indicators, and volume of the closing prices.
    Calculate the Risk/Reward Ratio. 
    CRITICAL INSTRUCTION: If the ratio between (target_price - entry_price) and (entry_price - stop_loss) is less than 1:2 (meaning potential reward is less than 2x the risk), you MUST set "recommendation" to "HOLD" or "NEUTRAL", not "BUY".
    Determine if this stock is a good BUY right now.
    
    Respond strictly in JSON format with the following schema:
    {{
        "ticker": "{ticker}",
        "recommendation": "BUY" | "HOLD" | "SELL" | "NEUTRAL",
        "confidence": <float 0.0 - 100.0>,
        "entry_price": <float recommended entry price>,
        "target_price": <float take profit target>,
        "stop_loss": <float cut loss limit>,
        "risk_reward_ratio": "<string e.g. '1:3' or '1:2.5'>",
        "estimated_days_to_target": <integer estimation of days to reach target frame>,
        "reasoning": "<short explanation based on the closing price trend and volume. MUST BE WRITTEN IN INDONESIAN LANGUAGE (BAHASA INDONESIA)>"
    }}
    """
    
    try:
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                )
            )
        except Exception as inner_e:
            if "429" in str(inner_e):
                logger.warning(f"Rate limit reached for gemini-2.5-flash on {ticker}. Falling back to gemini-2.0-flash...")
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    )
                )
            else:
                raise inner_e
        
        # Model is configured to return JSON application/json
        result = json.loads(response.text)
        logger.info(f"Successfully analyzed {ticker}. Recommendation: {result.get('recommendation')}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response from Gemini for {ticker}: {e}\nRaw Response: {response.text}")
    except Exception as e:
        logger.error(f"Error analyzing data with Gemini for {ticker}: {e}")
        
    return None

def analyze_ticker_with_indicators(ticker: str, current_price: float, sma: List[Dict], ema: List[Dict], macd: List[Dict], rsi: List[Dict]) -> Optional[Dict[str, Any]]:
    """
    Analyze technical data using Gemini for on-demand risk analysis.
    Uses purely technical logic without Grounding.
    """
    if not client:
        return None
        
    prompt = f"""
    Act as a Professional Risk and Technical Analyst specializing in swing trading (daily to weekly timeframe).
    Analyze the following technical indicators for the stock ticker {ticker}. All data series contain the last 50 trading days, with the most recent value at the end of the list.

    Current Close Price: {current_price}

    Indicator Data (last 50 days, most recent last):
    - SMA 20: {json.dumps(sma)}  (list of float values)
    - EMA 20: {json.dumps(ema)}  (list of float values)
    - MACD (8, 17, 9): {json.dumps(macd)}  (list of dicts with keys 'value', 'signal', 'histogram')
    - RSI (14): {json.dumps(rsi)}  (list of float values)

    RULES FOR ANALYSIS:
    1. **SMA 20 (Main Filter)**: Take the latest SMA 20 value (last element). If Current Price is below this value, the stock is in a short-term downtrend and considered higher risk for long positions.
    2. **EMA 20 (Trend Indicator)**: Compare the latest EMA value with the previous day's EMA (second last) to determine if the trend is up (latest > previous) or down (latest < previous).
    3. **MACD (Momentum Confirmation)**:
       - Check if the latest MACD line ('value') is above the Signal line ('signal') – bullish momentum.
       - Also check the histogram: if the latest histogram is positive and greater than the previous day's histogram, momentum is strengthening.
    4. **RSI (Overbought/Oversold)**:
       - Identify if latest RSI is overbought (>70), oversold (<30), or neutral.
       - If oversold and latest RSI > previous RSI, it signals potential recovery (bullish).
       - If overbought and latest RSI < previous RSI, it signals potential weakness (bearish).

    Combine these signals to determine a final recommendation:
    - **Bullish**: Price above SMA 20, EMA trending up, MACD bullish (value above signal and histogram positive/growing), and RSI not overbought (or recovering from oversold).
    - **Bearish**: Price below SMA 20, EMA trending down, MACD bearish (value below signal and histogram negative), and RSI not oversold (or falling from overbought).
    - **Neutral**: Mixed signals or no clear direction.

    CRITICAL: RETURN ONLY A RAW JSON OBJECT. Do not include any other text, explanations, or markdown.

    Format:
    {{
        "ticker": "{ticker}",
        "recommendation": "Bullish" | "Bearish" | "Neutral",
        "key_risks": "<string listing 1-2 main technical risks, punchy key risk in Indonesian>",
        "summary": "<Short, punchy summary in Indonesian>"
    }}
    """
    try:
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
        except Exception as inner_e:
            if "429" in str(inner_e):
                logger.warning(f"Rate limit reached for gemini-2.5-flash on {ticker}. Falling back to gemini-2.0-flash...")
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )
            else:
                raise inner_e
        
        raw_text = response.text.strip() if response.text else ""
        if not raw_text:
            return None

        # Robust cleaning
        processed_text = raw_text
        if "```json" in processed_text:
            processed_text = processed_text.split("```json")[1].split("```")[0].strip()
        elif "```" in processed_text:
            processed_text = processed_text.split("```")[1].split("```")[0].strip()
        
        processed_text = processed_text.strip()
        
        if not (processed_text.startswith("{") and processed_text.endswith("}")):
            start_idx = processed_text.find("{")
            end_idx = processed_text.rfind("}")
            if start_idx != -1 and end_idx != -1:
                processed_text = processed_text[start_idx:end_idx+1]
                
        result = json.loads(processed_text)
        logger.info(f"Technical Analysis completed for {ticker}: {result.get('recommendation')}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON for technical analysis {ticker}: {e}\n{raw_text[:200]}")
    except Exception as e:
        if "429" in str(e):
            logger.error(f"Gemini API Rate Limit Reached for {ticker} (429 RESOURCE_EXHAUSTED).")
            raise e
        logger.error(f"Error analyzing technical data with Gemini for {ticker}: {e}")
        
    return None
