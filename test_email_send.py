"""Test script to verify Resend email delivery using environment variables."""
import os
import json
import urllib.request
import urllib.error
from src.config import config

API_KEY = config.RESEND_API_KEY
TO_EMAIL = config.ALERT_EMAIL_TO or "ronabraham2000@gmail.com"
FROM_EMAIL = config.ALERT_EMAIL_FROM or "Shopping Deals <onboarding@resend.dev>"

if not API_KEY:
    print("❌ Error: RESEND_API_KEY is not set in .env")
    exit(1)

payload = {
    "from": FROM_EMAIL,
    "to": [TO_EMAIL],
    "subject": "🧪 Test Email from Shopping Deal Agent",
    "html": "<h3>Shopping Deal Agent Test</h3><p>This is a verification test to confirm Resend delivery is functioning properly without Cloudflare 1010 block.</p>"
}

print(f"Sending test email to {TO_EMAIL}...")
try:
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "resend-python/2.6.0",
            "Accept": "application/json"
        }
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        res = json.loads(resp.read().decode("utf-8"))
        print(f"SUCCESS! Resend Email ID: {res.get('id')}")
except urllib.error.HTTPError as e:
    print(f"HTTPError {e.code}: {e.read().decode('utf-8')}")
except Exception as e:
    print(f"Exception: {e}")
