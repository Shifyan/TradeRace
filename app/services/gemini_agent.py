import json
from google import genai
from google.genai import types
from typing import Dict, Any, Optional
from app.config import settings

client = genai.Client(api_key=settings.GEMINI_API_KEY)

def analyze_stock_data(ticker: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Analyze technical data using Gemini and return JSON representation."""
    prompt = f"""
    Analyze the following daily aggregate stock data for {ticker}.
    Data: {json.dumps(data)}
    
    Act as a Senior Financial Analyst. Determine if this stock is a good BUY.
    Respond strictly in JSON format with the following schema:
    {{
        "ticker": "{ticker}",
        "recommendation": "BUY" | "HOLD" | "SELL",
        "confidence": <float 0.0 - 100.0>,
        "reasoning": "<short explanation>"
    }}
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            )
        )
        
        # Model is configured to return JSON application/json
        result = json.loads(response.text)
        return result
    except Exception as e:
        print(f"Error analyzing data with Gemini: {e}")
        return None
