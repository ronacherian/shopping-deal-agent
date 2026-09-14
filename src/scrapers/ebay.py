"""eBay Refurbished marketplace scraper."""
import re
import urllib.parse
import logging
from typing import List
from src.models import RawListing
from src.scrapers.base import BaseScraper
from src.config import config

logger = logging.getLogger(__name__)

class EbayRefurbishedScraper(BaseScraper):
    name = "eBay Refurbished"

    def __init__(self):
        super().__init__()
        query = f"apple {config.TARGET_PRODUCT} m3"
        encoded = urllib.parse.quote_plus(query)
        # Condition codes: 2000 (Certified Refurbished), 2010 (Excellent), 2020 (Very Good), 2500 (Seller Refurbished), LH_BIN=1 (Buy It Now)
        self.url = f"https://www.ebay.com/sch/i.html?_nkw={encoded}&_sacat=111422&LH_ItemCondition=2000%7C2010%7C2020%7C2500&LH_BIN=1&_sop=15"

    def scrape(self) -> List[RawListing]:
        results = []
        html = self.fetch_url(self.url)
        if not html:
            return results

        # Match eBay s-item cards
        cards = re.findall(r'<div class="s-item__info[^"]*">(.*?)</div>\s*</div>', html, re.DOTALL)
        for card in cards:
            title_match = re.search(r'<div class="s-item__title"[^>]*><span[^>]*>(.*?)</span></div>', card)
            if not title_match:
                title_match = re.search(r'<h3 class="s-item__title"[^>]*>(.*?)</h3>', card)
            if not title_match:
                continue

            title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip()
            if not title or "Shop on eBay" in title:
                continue

            link_match = re.search(r'<a class="s-item__link"[^>]*href="([^"]+)"', card)
            if not link_match:
                continue
            url = link_match.group(1).split("?")[0]  # clean tracking params

            price_match = re.search(r'<span class="s-item__price">\$([0-9,.]+)</span>', card)
            if not price_match:
                price_match = re.search(r'\$([0-9]{3,4}\.[0-9]{2})', card)

            price = self.clean_price(price_match.group(1)) if price_match else None
            if not price or price < 200:
                continue

            item_id_match = re.search(r'/itm/(\d+)', url)
            unique_id = item_id_match.group(1) if item_id_match else title[:30]

            deal_id = self.generate_deal_id("ebay", unique_id)
            results.append(RawListing(
                id=deal_id,
                source="eBay Refurbished",
                title=title,
                price=price,
                url=url,
                condition="eBay Refurbished",
                raw_specs=title,
                category=config.CATEGORY
            ))

        logger.info(f"[{self.name}] Completed: {len(results)} listings fetched.")
        return results
