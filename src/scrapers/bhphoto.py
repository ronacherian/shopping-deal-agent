"""B&H Photo Used & Refurbished department scraper."""
import re
import urllib.parse
import logging
from typing import List
from src.models import RawListing
from src.scrapers.base import BaseScraper
from src.config import config

logger = logging.getLogger(__name__)

class BHPhotoScraper(BaseScraper):
    name = "B&H Photo Used"

    def __init__(self):
        super().__init__()
        query = f"{config.TARGET_PRODUCT} m3"
        encoded = urllib.parse.quote_plus(query)
        self.url = f"https://www.bhphotovideo.com/c/search?q={encoded}&filters=fct_category%3Aapple_laptops_95%2Cfct_condition_5587%3Aused"

    def scrape(self) -> List[RawListing]:
        results = []
        html = self.fetch_url(self.url)
        if not html:
            return results

        # Match B&H item cards
        cards = re.findall(r'<div[^>]*data-selenium="miniProductPage"[^>]*>(.*?)</div>\s*</div>\s*</div>', html, re.DOTALL)
        for card in cards:
            title_match = re.search(r'<span[^>]*data-selenium="miniProductPageProductName"[^>]*>([^<]+)</span>', card)
            if not title_match:
                continue
            title = title_match.group(1).strip()

            link_match = re.search(r'<a[^>]*data-selenium="miniProductPageProductNameLink"[^>]*href="([^"]+)"', card)
            if not link_match:
                continue
            link = link_match.group(1)
            url = f"https://www.bhphotovideo.com{link}" if link.startswith("/") else link

            price_match = re.search(r'<span[^>]*data-selenium="uppedDecimalPriceFinal"[^>]*>\$([0-9,.]+)</span>', card)
            if not price_match:
                price_match = re.search(r'\$([0-9]{3,4}\.[0-9]{2})', card)

            price = self.clean_price(price_match.group(1)) if price_match else None
            if not price or price < 200:
                continue

            sku_match = re.search(r'/c/product/(\d+)', url)
            unique_id = sku_match.group(1) if sku_match else title[:30]

            deal_id = self.generate_deal_id("bhphoto", unique_id)
            results.append(RawListing(
                id=deal_id,
                source="B&H Photo",
                title=title,
                price=price,
                url=url,
                condition="Used / Refurbished",
                raw_specs=title,
                category=config.CATEGORY
            ))

        logger.info(f"[{self.name}] Completed: {len(results)} listings fetched.")
        return results
