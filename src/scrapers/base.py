"""Base scraper class with anti-bot resilience and optional free proxy support."""
import os
import re
import gzip
import json
import logging
import urllib.parse
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from src.models import RawListing

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"macOS"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1"
}

class BaseScraper(ABC):
    name: str = "BaseScraper"

    def __init__(self, headers: Optional[Dict[str, str]] = None):
        self.headers = headers or DEFAULT_HEADERS.copy()
        self.scraper_api_key = os.getenv("SCRAPER_API_KEY", "")

    def fetch_url(self, url: str, extra_headers: Optional[Dict[str, str]] = None, timeout: int = 15) -> str:
        """Fetches raw HTML with automatic compression decoding and optional proxy routing."""
        target_url = url
        req_headers = self.headers.copy()

        if self.scraper_api_key:
            target_url = f"http://api.scraperapi.com?api_key={self.scraper_api_key}&url={urllib.parse.quote(url)}"
        elif extra_headers:
            req_headers.update(extra_headers)

        req = urllib.request.Request(target_url, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                content = response.read()
                if response.info().get("Content-Encoding") == "gzip" or (len(content) > 2 and content[:2] == b"\x1f\x8b"):
                    try:
                        content = gzip.decompress(content)
                    except Exception:
                        pass
                return content.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            logger.warning(f"[{self.name}] HTTP {e.code} error fetching {url}")
            return ""
        except Exception as e:
            logger.warning(f"[{self.name}] Error fetching {url}: {e}")
            return ""

    @staticmethod
    def clean_price(price_str: Any) -> Optional[float]:
        """Extracts float price from various string formats."""
        if price_str is None:
            return None
        if isinstance(price_str, (int, float)):
            return float(price_str)
        cleaned = re.sub(r"[^\d.]", "", str(price_str))
        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def generate_deal_id(source: str, unique_key: str) -> str:
        """Generates a stable deal ID."""
        clean_key = re.sub(r"[^a-zA-Z0-9_-]", "_", unique_key.strip())
        return f"{source.lower().replace(' ', '_')}_{clean_key}"

    @abstractmethod
    def scrape(self) -> List[RawListing]:
        """Executes the scraper and returns raw listings."""
        pass
