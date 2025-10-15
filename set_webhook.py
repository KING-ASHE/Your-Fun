import requests
import os
import sys

# Needs requests library (Add 'requests' to requirements.txt)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

if not BOT_TOKEN or not WEBHOOK_URL:
    print("Error: BOT_TOKEN or WEBHOOK_URL environment variable not set.")
    sys.exit(1)

webhook_full_url = f"{WEBHOOK_URL}/telegram_webhook"
tg_api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_full_url}"

print(f"Attempting to set webhook to: {webhook_full_url}")

try:
    response = requests.get(tg_api_url)
    response.raise_for_status() # Check for HTTP errors
    print(f"Webhook API Response: {response.json()}")
    if response.json().get('ok'):
        print("Webhook set successfully!")
    else:
        print("Webhook set failed!")
        sys.exit(1)
except Exception as e:
    print(f"Error setting webhook: {e}")
    sys.exit(1)