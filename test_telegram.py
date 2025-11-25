"""
Quick Telegram Test Script
"""
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    print("❌ Error: TELEGRAM_TOKEN or TELEGRAM_CHAT_ID not found in .env")
    exit(1)

# Test Message
message = f"""
🚀 <b>M7 Dashboard Test Alert</b>

🎯 <b>Ticker:</b> MSFT
💵 <b>Price:</b> $472.12
📊 <b>Score:</b> 100/100

📈 <b>Signal:</b>
RSI 28.4 과매도 + 단기 상승 추세

🛡️ <b>Strategy:</b>
• Stop Loss: $462.26
• Take Profit: $482.48

<i>⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</i>
"""

url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
data = {
    "chat_id": CHAT_ID,
    "text": message,
    "parse_mode": "HTML"
}

print("📱 Sending test message to Telegram...")
response = requests.post(url, data=data, timeout=10)

if response.status_code == 200:
    print("✅ Success! Message sent to Telegram!")
    print(f"Response: {response.json()}")
else:
    print(f"❌ Failed! Status code: {response.status_code}")
    print(f"Response: {response.text}")
