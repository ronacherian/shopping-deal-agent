"""Best Buy Outlet / Refurbished scraper."""
import re
import urllib.parse
import logging
from typing import List
from src.models import RawListing
from src.scrapers.base import BaseScraper
from src.config import config

logger = logging.getLogger(__name__)

class BestBuyScraper(BaseScraper):
    name = "Best Buy Refurbished"

    def __init__(self):
        super().__init__()
        query = f"refurbished {config.TARGET_PRODUCT} m3"
        encoded_query = urllib.parse.quote(query)
        self.url = f"https://www.bestbuy.com/site/searchpage.jsp?st={encoded_query}"

    def scrape(self) -> List[RawListing]:
        results = []
        html = self.fetch_url(self.url)
        if not html:
            return results

        # Best Buy product card regex
        item_blocks = re.findall(r'<li class="sku-item"[^>]*>(.*?)</li>\s*(?=<li class="sku-item"|</ul>)', html, re.DOTALL)
        if not item_blocks:
            # Alternate block matching
            item_blocks = re.findall(r'<div class="sku-item-content"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)

        for block in item_blocks:
            # Extract SKU
            sku_match = re.search(r'data-sku-id="(\d+)"', block)
            sku = sku_match.group(1) if sku_match else ""

            # Extract Title & URL
            title_match = re.search(r'<h4 class="sku-title"[^>]*>\s*<a href="([^"]+)"[^>]*>([^<]+)</a>', block)
            if not title_match:
                title_match = re.search(r'<a class="image-link"[^>]*href="([^"]+)"[^>]*title="([^"]+)"', block)

            if not title_match:
                continue

            link_path, title = title_match.group(1), title_match.group(2).strip()
            full_url = f"https://www.bestbuy.com{link_path}" if link_path.startswith("/") else link_path

            # Extract Price
            price_match = re.search(r'class="priceView-customer-price"[^>]*>\s*<span aria-hidden="true">\$([0-9,.]+)</span>', block)
            if not price_match:
                price_match = re.search(r'\$([0-9]{3,4}\.[0-9]{2})', block)

            price = self.clean_price(price_match.group(1)) if price_match else None
            if not price:
                continue

            deal_id = self.generate_deal_id("bestbuy", sku or title[:30])
            results.append(RawListing(
                id=deal_id,
                source="Best Buy",
                title=title,
                price=price,
                url=full_url,
                condition="Refurbished / Open-Box",
                raw_specs=title,
                category=config.CATEGORY
            ))

        logger.info(f"[{self.name}] Completed: {len(results)} listings fetched.")
        return results
