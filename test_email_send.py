"""Manual test script to verify Resend email delivery using environment variables."""
import json
import urllib.error
import urllib.request
from src.config import config


def send_test_email() -> None:
    api_key = config.RESEND_API_KEY
    to_email = config.ALERT_EMAIL_TO or "ronabraham2000@gmail.com"
    from_email = config.ALERT_EMAIL_FROM or "Shopping Deals <onboarding@resend.dev>"

    if not api_key:
        print("❌ Error: RESEND_API_KEY is not set in .env")
        return

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": "🧪 Test Email from Shopping Deal Agent",
        "html": (
            "<h3>Shopping Deal Agent Test</h3>"
            "<p>This is a verification test to confirm Resend delivery is functioning properly.</p>"
        ),
    }

    print(f"Sending test email to {to_email}...")
    try:
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "resend-python/2.6.0",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            print(f"SUCCESS! Resend Email ID: {res.get('id')}")
    except urllib.error.HTTPError as e:
        print(f"HTTPError {e.code}: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"Exception: {e}")


if __name__ == "__main__":
    send_test_email()
