import requests
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

def send_ntfy_notification(title: str, message: str) -> bool:
    """Send a push notification via Ntfy.sh."""
    url = f"https://ntfy.sh/{settings.NTFY_TOPIC}"
    
    # Ntfy headers must be ASCII/Latin-1 safe by default in python requests.
    # We use tags for emojis instead of putting them in the Title.
    headers = {
        "Title": title.encode('ascii', 'ignore').decode('ascii'),
        "Tags": "chart_with_upwards_trend,moneybag"
    }
    
    try:
        response = requests.post(
            url, 
            data=message.encode('utf-8'), 
            headers=headers, 
            timeout=5
        )
        response.raise_for_status()
        logger.info(f"Notification sent successfully: {title}")
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to send Ntfy notification '{title}': {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error while sending notification: {e}")
        return False
