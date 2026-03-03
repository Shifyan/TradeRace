from openai import OpenAI
from app.config import settings
from typing import Dict, Any, Optional, List
from app.utils.logger import get_logger

logger = get_logger(__name__)

class DeepSeekAgent:
    def __init__(self):
        try:
            self.client = OpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        except Exception as e:
            logger.error(f"Error initializing DeepSeek client: {e}")
            self.client = None

    def query_deepseek(self) -> List[str]:
        """Provides stock recommendations based on news."""
        if self.client is None:
            logger.error("DeepSeek client not initialized.")
            return []

        prompt = """
        You are a helpful assistant that provides stock recommendations based on news. The response must be a JSON array.
        """

        userPrompt = """    give me recommendation indonesia stocks."""
        try:
            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": userPrompt},
                ],
                response_format={"type": "json_object"},
                stream=False
            )
            # Extract the JSON array from the response
            if response and hasattr(response, 'choices'):
                return [choice.message.content for choice in response.choices]
            else:
                logger.error("Unexpected response format from DeepSeek API.")
                return []
        except Exception as e:
            logger.error(f"Error querying DeepSeek: {e}")
            return []
            
    # Add new specific DeepSeek methods here without breaking Gemini
    # def deepseek_specific_analysis(self, data):
    #     pass

# Export a single global instance
deepseek_agent = DeepSeekAgent()