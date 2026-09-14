"""Back Market refurbished marketplace scraper."""
import re
import urllib.parse
import logging
from typing import List
from src.models import RawListing
from src.scrapers.base import BaseScraper
from src.config import config

logger = logging.getLogger(__name__)

class BackMarketScraper(BaseScraper):
    name = "Back Market"

    def __init__(self):
        super().__init__()
        query = f"{config.TARGET_PRODUCT} M3"
        encoded = urllib.parse.quote_plus(query)
        self.url = f"https://www.backmarket.com/en-us/search?q={encoded}"

    def scrape(self) -> List[RawListing]:
        results = []
        html = self.fetch_url(self.url)
        if not html:
            return results

        # Back Market product cards
        cards = re.findall(r'<div[^>]*data-qa="product-card"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
        if not cards:
            cards = re.findall(r'<a[^>]*href="(/en-us/p/[^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL)
            for path, inner in cards:
                title_match = re.search(r'<h2[^>]*>([^<]+)</h2>', inner)
                if not title_match:
                    continue
                title = title_match.group(1).strip()
                price_match = re.search(r'\$([0-9,.]+)', inner)
                price = self.clean_price(price_match.group(1)) if price_match else None
                if not price or price < 200:
                    continue
                full_url = f"https://www.backmarket.com{path}"
                deal_id = self.generate_deal_id("backmarket", path)
                results.append(RawListing(
                    id=deal_id,
                    source="Back Market",
                    title=title,
                    price=price,
                    url=full_url,
                    condition="Refurbished",
                    raw_specs=title,
                    category=config.CATEGORY
                ))
            logger.info(f"[{self.name}] Completed: {len(results)} listings fetched.")
            return results

        for card in cards:
            link_match = re.search(r'href="([^"]+)"', card)
            title_match = re.search(r'<h2[^>]*>([^<]+)</h2>', card)
            price_match = re.search(r'\$([0-9,.]+)', card)

            if not (link_match and title_match and price_match):
                continue

            link = link_match.group(1)
            full_url = f"https://www.backmarket.com{link}" if link.startswith("/") else link
            title = title_match.group(1).strip()
            price = self.clean_price(price_match.group(1))

            if price and price >= 200:
                deal_id = self.generate_deal_id("backmarket", link)
                results.append(RawListing(
                    id=deal_id,
                    source="Back Market",
                    title=title,
                    price=price,
                    url=full_url,
                    condition="Refurbished",
                    raw_specs=title,
                    category=config.CATEGORY
                ))

        logger.info(f"[{self.name}] Completed: {len(results)} listings fetched.")
        return results
