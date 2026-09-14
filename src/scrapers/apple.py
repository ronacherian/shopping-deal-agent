"""Apple Certified Refurbished store scraper."""
import re
import json
import logging
from typing import List
from src.models import RawListing
from src.scrapers.base import BaseScraper
from src.config import config

logger = logging.getLogger(__name__)

class AppleRefurbishedScraper(BaseScraper):
    name = "Apple Refurbished"

    def __init__(self):
        super().__init__()
        # Extensible category/product path
        self.url = "https://www.apple.com/shop/refurbished/mac/macbook-pro"

    def scrape(self) -> List[RawListing]:
        results = []
        html = self.fetch_url(self.url)
        if not html:
            return results

        # 1. Try parsing JSON bootstrap data
        json_matches = re.findall(r"window\.REFURB_GRID_BOOTSTRAP\s*=\s*({.*?});</script>", html, re.DOTALL)
        if json_matches:
            try:
                data = json.loads(json_matches[0])
                tiles = data.get("tiles", []) or data.get("body", {}).get("tiles", [])
                for tile in tiles:
                    title = tile.get("title", "")
                    price_info = tile.get("price", {})
                    price_val = price_info.get("currentPrice", {}).get("raw_amount") or price_info.get("currentPrice", {}).get("amount")
                    price = self.clean_price(price_val)
                    part_no = tile.get("partNumber", "")
                    rel_url = tile.get("productDetailsUrl", "")
                    full_url = f"https://www.apple.com{rel_url}" if rel_url.startswith("/") else rel_url

                    if title and price:
                        results.append(RawListing(
                            id=self.generate_deal_id("apple", part_no or title),
                            source="Apple Certified Refurbished",
                            title=title,
                            price=price,
                            url=full_url or self.url,
                            condition="Apple Certified Refurbished",
                            raw_specs=title,
                            category=config.CATEGORY
                        ))
                if results:
                    logger.info(f"[{self.name}] Extracted {len(results)} listings via bootstrap JSON.")
                    return results
            except Exception as e:
                logger.debug(f"[{self.name}] Error parsing bootstrap JSON: {e}")

        # 2. Fallback regex extraction on product tiles
        tile_pattern = re.compile(
            r'class="as-macb-producttile".*?href="([^"]+)".*?aria-label="([^"]+)".*?class="as-price-currentprice">([^<]+)<',
            re.DOTALL
        )
        for match in tile_pattern.finditer(html):
            url_path, title, price_str = match.groups()
            price = self.clean_price(price_str)
            if price and title:
                full_url = f"https://www.apple.com{url_path}" if url_path.startswith("/") else url_path
                results.append(RawListing(
                    id=self.generate_deal_id("apple", title[:40]),
                    source="Apple Certified Refurbished",
                    title=title.strip(),
                    price=price,
                    url=full_url,
                    condition="Apple Certified Refurbished",
                    raw_specs=title.strip(),
                    category=config.CATEGORY
                ))

        logger.info(f"[{self.name}] Completed: {len(results)} listings fetched.")
        return results
