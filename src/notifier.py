"""Email notification generator and dispatcher using Resend API."""
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime
from typing import List
from src.config import config
from src.models import ParsedDeal

logger = logging.getLogger(__name__)

class EmailNotifier:
    def __init__(self):
        self.api_key = config.RESEND_API_KEY
        self.email_to = config.ALERT_EMAIL_TO
        self.email_from = config.ALERT_EMAIL_FROM

    def generate_html(self, deals: List[ParsedDeal], is_baseline: bool = False) -> str:
        """Generates a responsive HTML email digest for discovered deals."""
        now_str = datetime.utcnow().strftime("%B %d, %Y at %H:%M UTC")

        cards_html = ""
        for deal in deals:
            storage_tb = deal.storage_gb / 1000.0
            storage_str = f"{int(storage_tb)}TB" if storage_tb.is_integer() else f"{storage_tb}TB"
            savings_html = f'<span style="background:#e6f4ea; color:#137333; font-weight:600; padding:2px 8px; border-radius:12px; font-size:13px; margin-left:8px;">Save ${deal.savings:.0f}</span>' if deal.savings else ""

            cards_html += f"""
            <div style="background:#ffffff; border:1px solid #e0e0e0; border-radius:12px; padding:20px; margin-bottom:20px; box-shadow:0 2px 6px rgba(0,0,0,0.05);">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                    <span style="background:#f1f3f4; color:#3c4043; font-size:12px; font-weight:700; text-transform:uppercase; padding:4px 10px; border-radius:6px; letter-spacing:0.5px;">
                        {deal.source}
                    </span>
                    <span style="background:#fef7e0; color:#b06000; font-size:12px; font-weight:700; padding:4px 10px; border-radius:6px;">
                        Deal Score: {deal.deal_score}/10
                    </span>
                </div>

                <h3 style="margin:0 0 10px 0; font-size:17px; color:#1a73e8; line-height:1.4;">
                    <a href="{deal.url}" target="_blank" style="color:#1a73e8; text-decoration:none;">{deal.title}</a>
                </h3>

                <div style="margin:12px 0;">
                    <span style="font-size:24px; font-weight:800; color:#202124;">${deal.price:,.2f}</span>
                    {savings_html}
                </div>

                <div style="margin:14px 0; display:flex; flex-wrap:wrap; gap:8px;">
                    <span style="background:#e8f0fe; color:#1967d2; font-size:13px; font-weight:600; padding:4px 10px; border-radius:6px;">
                        ⚡ {deal.chip}
                    </span>
                    <span style="background:#e8f0fe; color:#1967d2; font-size:13px; font-weight:600; padding:4px 10px; border-radius:6px;">
                        🧠 {deal.ram_gb}GB RAM
                    </span>
                    <span style="background:#e8f0fe; color:#1967d2; font-size:13px; font-weight:600; padding:4px 10px; border-radius:6px;">
                        💾 {storage_str} SSD
                    </span>
                    <span style="background:#f1f3f4; color:#5f6368; font-size:13px; padding:4px 10px; border-radius:6px;">
                        🖥️ {deal.screen_size}
                    </span>
                    <span style="background:#f1f3f4; color:#5f6368; font-size:13px; padding:4px 10px; border-radius:6px;">
                        🏷️ {deal.condition}
                    </span>
                </div>

                {f'<div style="background:#f8f9fa; border-left:4px solid #1a73e8; padding:10px 14px; border-radius:4px; font-size:13px; color:#3c4043; line-height:1.5; margin-bottom:14px;"><strong>AI Assessment:</strong> {deal.gemini_analysis}</div>' if deal.gemini_analysis else ''}

                <a href="{deal.url}" target="_blank" style="display:inline-block; background:#1a73e8; color:#ffffff; font-weight:700; font-size:14px; text-decoration:none; padding:10px 20px; border-radius:8px; text-align:center;">
                    View & Buy on {deal.source} &rarr;
                </a>
            </div>
            """

        banner_text = f"{config.TARGET_PRODUCT} Deal Alert" if not is_baseline else "Shopping Deal Agent: Initial Baseline Report"
        sub_text = (
            f"Found <strong>{len(deals)}</strong> deal(s) matching your criteria: <strong>M3+ | &ge; 24GB RAM | &ge; 1TB SSD | &lt; $1,990</strong>"
            if not is_baseline else
            f"Agent is now active in AWS! Cataloged <strong>{len(deals)}</strong> current deals into DynamoDB. Monitoring every 6 hours for your target criteria."
        )

        html_wrapper = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{banner_text}</title>
</head>
<body style="font-family:-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background:#f8f9fa; margin:0; padding:24px 12px; color:#202124;">
    <div style="max-width:640px; margin:0 auto;">
        <div style="text-align:center; margin-bottom:28px;">
            <div style="font-size:32px; margin-bottom:6px;">🛍️ {'🔥' if not is_baseline else '✅'}</div>
            <h1 style="font-size:22px; font-weight:800; margin:0 0 6px 0; color:#202124;">
                {banner_text}
            </h1>
            <p style="margin:0; font-size:13px; color:#5f6368; line-height:1.5;">
                {sub_text}<br>
                Scanned on {now_str}
            </p>
        </div>

        {cards_html}

        <div style="text-align:center; font-size:12px; color:#80868b; margin-top:32px; border-top:1px solid #e0e0e0; padding-top:16px;">
            <p style="margin:4px 0;">Generated automatically by your Serverless Shopping Deal Agent on AWS Lambda.</p>
            <p style="margin:4px 0;">All deals are stored and tracked in your Amazon DynamoDB table.</p>
        </div>
    </div>
</body>
</html>
"""
        return html_wrapper

    def send_alert(self, deals: List[ParsedDeal], is_baseline: bool = False) -> bool:
        """Dispatches email alert via Resend API."""
        if not deals:
            logger.info("No deals to alert.")
            return True

        if not self.api_key or not self.email_to:
            logger.warning("RESEND_API_KEY or ALERT_EMAIL_TO not set. Saving preview to latest_deal_email.html")
            try:
                html_preview = self.generate_html(deals, is_baseline=is_baseline)
                with open("latest_deal_email.html", "w") as f:
                    f.write(html_preview)
                logger.info("Preview saved to latest_deal_email.html")
            except Exception as e:
                logger.error(f"Failed to write preview HTML: {e}")
            return False

        if is_baseline:
            subject = f"✅ Shopping Deal Agent is LIVE! (Baseline Scan: {len(deals)} Deals Cataloged)"
        else:
            subject = f"🔥 {len(deals)} New {config.TARGET_PRODUCT} Deal{'s' if len(deals) > 1 else ''} (<$1,990)"

        html_content = self.generate_html(deals, is_baseline=is_baseline)

        payload = {
            "from": self.email_from,
            "to": [self.email_to],
            "subject": subject,
            "html": html_content
        }

        # 1. Try official Resend Python SDK if installed
        try:
            import resend
            resend.api_key = self.api_key
            result = resend.Emails.send(payload)
            email_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", "sent")
            logger.info(f"Successfully sent email via Resend SDK (ID: {email_id}) to {self.email_to}")
            return True
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"Resend SDK issue ({e}), trying direct HTTP")

        # 2. Fallback: Direct HTTP POST with custom User-Agent to avoid Cloudflare 1010 block
        try:
            req_body = json.dumps(payload).encode("utf-8")
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "resend-python/2.6.0",
                "Accept": "application/json"
            }
            req = urllib.request.Request("https://api.resend.com/emails", data=req_body, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                email_id = result.get("id")
                logger.info(f"Successfully sent email via Resend API (ID: {email_id}) to {self.email_to}")
                return True
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            logger.error(f"Resend API Error {e.code}: {err_body}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error dispatching email via Resend: {e}")
            return False
