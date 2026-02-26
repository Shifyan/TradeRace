import requests
from app.config import settings

def send_ntfy_notification(title: str, message: str) -> bool:
    """Send a push notification via Ntfy.sh."""
    url = f"https://ntfy.sh/{settings.NTFY_TOPIC}"
    
    headers = {
        "Title": title,
        "Tags": "chart_with_upwards_trend,moneybag"
    }
    
    response = requests.post(url, data=message.encode('utf-8'), headers=headers)
    return response.status_code == 200
