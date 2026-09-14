"""Amazon Renewed marketplace scraper."""
import re
import urllib.parse
import logging
from typing import List
from src.models import RawListing
from src.scrapers.base import BaseScraper
from src.config import config

logger = logging.getLogger(__name__)

class AmazonRenewedScraper(BaseScraper):
    name = "Amazon Renewed"

    def __init__(self):
        super().__init__()
        query = f"{config.TARGET_PRODUCT} renewed m3"
        encoded_query = urllib.parse.quote_plus(query)
        self.url = f"https://www.amazon.com/s?k={encoded_query}"

    def scrape(self) -> List[RawListing]:
        results = []
        html = self.fetch_url(self.url)
        if not html:
            return results

        # Amazon search items matching
        item_blocks = re.findall(r'<div[^>]*data-component-type="s-search-result"[^>]*>(.*?)</div>\s*</div>\s*</div>\s*</div>', html, re.DOTALL)
        for block in item_blocks:
            asin_match = re.search(r'data-asin="([A-Z0-9]{10})"', block)
            asin = asin_match.group(1) if asin_match else ""

            title_match = re.search(r'<h2[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>\s*<span[^>]*>([^<]+)</span>', block)
            if not title_match:
                title_match = re.search(r'<span class="a-size-medium a-color-base a-text-normal">([^<]+)</span>', block)
                if not title_match:
                    continue
                title = title_match.group(1).strip()
                link_match = re.search(r'href="(/dp/[^"]+)"', block)
                url = f"https://www.amazon.com{link_match.group(1)}" if link_match else self.url
            else:
                url = f"https://www.amazon.com{title_match.group(1)}" if title_match.group(1).startswith("/") else title_match.group(1)
                title = title_match.group(2).strip()

            price_match = re.search(r'<span class="a-price-whole">([0-9,]+)</span><span class="a-price-fraction">([0-9]{2})</span>', block)
            if price_match:
                price_str = f"{price_match.group(1)}.{price_match.group(2)}"
            else:
                price_match_simple = re.search(r'<span class="a-offscreen">\$([0-9,.]+)</span>', block)
                price_str = price_match_simple.group(1) if price_match_simple else None

            price = self.clean_price(price_str)
            if not price or price < 200:
                continue

            deal_id = self.generate_deal_id("amazon", asin or title[:30])
            results.append(RawListing(
                id=deal_id,
                source="Amazon Renewed",
                title=title,
                price=price,
                url=url,
                condition="Renewed",
                raw_specs=title,
                category=config.CATEGORY
            ))

        logger.info(f"[{self.name}] Completed: {len(results)} listings fetched.")
        return results
