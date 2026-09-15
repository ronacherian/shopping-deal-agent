"""Extensible configuration settings for the shopping deal agent."""
import os
from typing import List

def _load_env_file():
    """Lightweight loader for .env without requiring python-dotenv."""
    for path in [".env", os.path.join(os.path.dirname(__file__), "..", ".env")]:
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k not in os.environ:
                                os.environ[k] = v
                break
            except Exception:
                pass

_load_env_file()

class Config:
    # Target Item Description & Category
    TARGET_PRODUCT: str = os.getenv("TARGET_PRODUCT", "MacBook Pro / Air")
    CATEGORY: str = os.getenv("CATEGORY", "Laptops")

    # Hardware Criteria
    MAX_PRICE: float = float(os.getenv("MAX_PRICE", "1990.0"))
    MIN_RAM_GB: int = int(os.getenv("MIN_RAM_GB", "24"))
    MIN_STORAGE_GB: int = int(os.getenv("MIN_STORAGE_GB", "1000"))
    MIN_CHIP_GEN: int = int(os.getenv("MIN_CHIP_GEN", "3"))

    ALLOWED_CHIP_FAMILIES: List[str] = [
        "m3", "m3 pro", "m3 max",
        "m4", "m4 pro", "m4 max"
    ]

    # Email Alert Settings (Resend API)
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    ALERT_EMAIL_TO: str = os.getenv("ALERT_EMAIL_TO", "")
    ALERT_EMAIL_FROM: str = os.getenv("ALERT_EMAIL_FROM", "Shopping Deals <onboarding@resend.dev>")

    # Gemini Flash AI API Settings
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Proxy Settings (optional free ScraperAPI key)
    SCRAPER_API_KEY: str = os.getenv("SCRAPER_API_KEY", "")

    # Storage & Persistence (AWS DynamoDB with Local fallback)
    DYNAMODB_TABLE_NAME: str = os.getenv("DYNAMODB_TABLE_NAME", "MacBookDeals")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    LOCAL_STATE_FILE: str = os.getenv("LOCAL_STATE_FILE", ".seen_deals.json")
    DEAL_TTL_DAYS: int = int(os.getenv("DEAL_TTL_DAYS", "14"))

    # Operational Modes
    IS_LAMBDA: bool = bool(os.getenv("AWS_LAMBDA_FUNCTION_NAME"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

config = Config()
