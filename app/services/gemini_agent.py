import json
from google import genai
from google.genai import types
from typing import Dict, Any, Optional, List
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

class GeminiAgent:
    def __init__(self):
        try:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Client: {e}")
            self.client = None

    def get_top_tickers_by_sentiment(self) -> List[Dict[str, str]]:
        """
        Act as a Macro Economist. Uses Google Search Grounding to find the latest
        economic, political, and market news to determine the top 10 potential tickers.
        """
        if not self.client:
            logger.error("Gemini client is not initialized. Cannot get top tickers.")
            return []
            
        prompt = """
        Act as a Macro Economist and Swing Trading Analyst. Use Google Search Grounding to find the latest economic, political, and market news.

        **Objective:**
        Identify **1 to 5 US stocks** with the strongest positive catalysts for a **swing trade (holding period: 2 days to 2 weeks)** based on today's news. Focus on sectors benefiting from current macro narratives (e.g., falling yields, commodity shifts, policy changes).

        **Positive Catalysts Examples:**
        - Analyst upgrades or price target raises.
        - New product launches or regulatory approvals.
        - Sector-specific tailwinds (e.g., energy due to oil prices).
        - Earnings surprises (but avoid stocks reporting in the next 5 days).

        **Filtering:**
        - EXCLUDE stocks scheduled to report earnings within the next 5 trading days.
        - EXCLUDE stocks that gapped up more than 5% pre-market unless the gap has held with volume support (price currently above the gap level).
        - No need to check technicals (like EMA) at this stage; we will do that later.

        **Output Format:**
        Return a JSON array of objects with ticker and a brief catalyst description.
        [
            {"ticker": "TICKER1", "catalyst": "short reason"},
            ...
        ]
        """
        
        try:
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[{'google_search': {}}] # Enable Google Search Grounding
                    )
                )
            except Exception as inner_e:
                if "429" in str(inner_e):
                    logger.warning("Rate limit reached for gemini-2.5-flash on sentiment analysis. Falling back to gemini-2.0-flash...")
                    response = self.client.models.generate_content(
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
                # Clean and validate the list of objects
                results = []
                for item in tickers[:10]:
                    if isinstance(item, dict) and "ticker" in item:
                        results.append({
                            "ticker": str(item["ticker"]).upper().strip(),
                            "catalyst": str(item.get("catalyst", "No specific catalyst provided.")).strip()
                        })
                    elif isinstance(item, str):
                        results.append({
                            "ticker": item.upper().strip(),
                            "catalyst": "No specific catalyst provided."
                        })
                
                logger.info(f"AI Selected Top Tickers with Catalysts: {results}")
                return results
            else:
                logger.error(f"AI returned invalid format (not a list) for top tickers: {type(tickers)}")
                return []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response from Gemini Grounding: {e}. Raw content was: {raw_text[:200]}...")
            return []
        except Exception as e:
            logger.error(f"Error fetching top tickers via Gemini Grounding: {e}")
            return []

    def analyze_stock_data(self, ticker: str, data: List[Dict[str, Any]], sma_20, ema_20, macd, rsi, catalyst: str = "") -> Optional[Dict[str, Any]]:
        """Analyze historical technical data using Gemini and return JSON representation."""
        if not self.client:
            logger.error("Gemini client is not initialized. Cannot analyze data.")
            return None
            
        # Extract only essential data to save tokens (e.g., closing prices and volume)
        simplified_data = [{"c": d.get("c"), "v": d.get("v"), "t": d.get("t")} for d in data]
        
            
        prompt_sesi2 = f"""
        Analyze the following historical daily aggregate stock data for {ticker} over the last 60 trading days.
        The data is an array of records where 'c' is closing price, 'v' is volume, 't' is unix timestamp.

        Data:
        {json.dumps(simplified_data)}

        Catalyst (Fundamental News):
        {catalyst}

        Indicators (pre-calculated):
        - SMA 20: {json.dumps(sma_20)}
        - EMA 20: {json.dumps(ema_20)}
        - MACD (8,17,9): {json.dumps(macd)}  (list of dicts with 'value','signal','histogram')
        - RSI (14): {json.dumps(rsi)}

        Act as a Senior Technical Analyst. Analyze trend, momentum, and volume.

        **Rules for Entry, Stop Loss, Target:**
        - Entry Price: Use the latest closing price.
        - Stop Loss: Place below the nearest support level (e.g., recent swing low or below EMA 20 if it acted as support). If no clear support, use 1.5x ATR below entry.
        - Target Price: Based on nearest resistance level (recent swing high) or a risk/reward ratio of at least 1:2. If no clear resistance, use Fibonacci extension or 2x ATR above entry.
        - Risk/Reward Ratio: Calculate as (target - entry) / (entry - stop). If ratio < 2, you MUST set recommendation to "HOLD" or "NEUTRAL", not "BUY".

        **Confidence:** Based on confluence of indicators (e.g., MACD bullish cross, RSI >50, volume > average). 0-100%.

        **Estimated Days:** Use typical swing trade duration (2-10 days) based on volatility and trend strength.

        **Reasoning:** Explain in Bahasa Indonesia, covering trend, volume, and indicator signals.

        Respond strictly in JSON:
        {{
            "ticker": "{ticker}",
            "recommendation": "BUY" | "HOLD" | "SELL" | "NEUTRAL",
            "confidence": float,
            "entry_price": float,
            "target_price": float,
            "stop_loss": float,
            "risk_reward_ratio": "1:x.x",
            "estimated_days_to_target": integer,
            "reasoning": "string in Indonesian",
            "catalyst": "string in Indonesian"
        }}
        """
        
        try:
            try:
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt_sesi2,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    )
                )
            except Exception as inner_e:
                if "429" in str(inner_e):
                    logger.warning(f"Rate limit reached for gemini-2.5-flash on {ticker}. Falling back to gemini-2.0-flash...")
                    # Note: fixing a variable scope bug present from previous versions
                    response = self.client.models.generate_content(
                        model="gemini-2.0-flash",
                        contents=prompt_sesi2,
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

    def analyze_ticker_with_indicators(self, ticker: str, current_price: float, sma: List[Dict], ema: List[Dict], macd: List[Dict], rsi: List[Dict]) -> Optional[Dict[str, Any]]:
        """
        Analyze technical data using Gemini for on-demand risk analysis.
        Uses purely technical logic without Grounding.
        """
        if not self.client:
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
                response = self.client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=prompt
                )
            except Exception as inner_e:
                if "429" in str(inner_e):
                    logger.warning(f"Rate limit reached for gemini-2.5-flash on {ticker}. Falling back to gemini-2.0-flash...")
                    response = self.client.models.generate_content(
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

# Export a single global instance
gemini_agent = GeminiAgent()
