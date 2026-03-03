from openai import OpenAI
from app.config import settings
from typing import Dict, Any, Optional, List


try:
    client = OpenAI(api_key=settings.DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
except Exception as e:
    print(f"Error initializing DeepSeek client: {e}")
    client = None


def query_deepseek() -> List[str]:
    if client is None:
        print("DeepSeek client not initialized.")
        return []  # Return an empty list to match the expected return type

    prompt = """
    You are a helpful assistant that provides stock recommendations based on news. The response must be a JSON array.
    """

    userPrompt = """    give me recommendation indonesia stocks."""
    try:
        response = client.chat.completions.create(
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
            return [choice.message['content'] for choice in response.choices]
        else:
            print("Unexpected response format from DeepSeek API.")
            return []
    except Exception as e:
        print(f"Error querying DeepSeek: {e}")
        return []