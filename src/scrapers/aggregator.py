"""Scraper for curated refurbished and shopping deals across Apple, Best Buy, Amazon, B&H, and eBay."""
import re
import html
import logging
import xml.etree.ElementTree as ET
from typing import List
from src.models import RawListing
from src.scrapers.base import BaseScraper
from src.config import config

logger = logging.getLogger(__name__)

class DealAggregatorScraper(BaseScraper):
    name = "Refurbished Deal Feeds"

    def __init__(self):
        super().__init__()
        query = config.TARGET_PRODUCT.replace(" ", "+").lower()
        self.feed_urls = [
            f"https://slickdeals.net/newsearch.php?q={query}&pp=20&sort=newest&rating=0&forumid%5B%5D=9&hideexpired=1&rss=1",
            "https://www.dealnews.com/c49/Computers/Laptops/Mac-Books/?rss=1"
        ]

    def _extract_items_via_regex(self, xml_text: str) -> List[dict]:
        """Robust fallback extraction if ElementTree encounters namespace issues."""
        items = []
        raw_items = re.findall(r"<item>(.*?)</item>", xml_text, re.DOTALL | re.IGNORECASE)
        for raw in raw_items:
            title_m = re.search(r"<title>(?:<!\[CDATA\[(.*?)\]\]>|(.*?))</title>", raw, re.DOTALL | re.IGNORECASE)
            title = ""
            if title_m:
                title = title_m.group(1) or title_m.group(2) or ""
                title = html.unescape(title.strip())

            link_m = re.search(r"<link>(?:<!\[CDATA\[(.*?)\]\]>|(.*?))</link>", raw, re.DOTALL | re.IGNORECASE)
            link = ""
            if link_m:
                link = link_m.group(1) or link_m.group(2) or ""
                link = link.strip()

            desc_m = re.search(r"<description>(?:<!\[CDATA\[(.*?)\]\]>|(.*?))</description>", raw, re.DOTALL | re.IGNORECASE)
            desc = ""
            if desc_m:
                desc = desc_m.group(1) or desc_m.group(2) or ""
                desc = html.unescape(desc.strip())

            guid_m = re.search(r"<guid.*?>(?:<!\[CDATA\[(.*?)\]\]>|(.*?))</guid>", raw, re.DOTALL | re.IGNORECASE)
            guid = ""
            if guid_m:
                guid = guid_m.group(1) or guid_m.group(2) or ""
                guid = guid.strip()

            if title and link:
                items.append({
                    "title": title,
                    "link": link,
                    "desc": desc,
                    "guid": guid or link
                })
        return items

    def scrape(self) -> List[RawListing]:
        listings: List[RawListing] = []
        target_words = [w.lower() for w in config.TARGET_PRODUCT.split()]

        for url in self.feed_urls:
            xml_text = self.fetch_url(url, timeout=12)
            if not xml_text:
                continue

            parsed_items = []
            try:
                # Remove namespaces to simplify parsing
                xml_clean = re.sub(r' xmlns(:\w+)?="[^"]+"', '', xml_text, count=1)
                root = ET.fromstring(xml_clean)
                channel = root.find("channel")
                if channel is not None:
                    for item in channel.findall("item"):
                        t_elem = item.find("title")
                        l_elem = item.find("link")
                        d_elem = item.find("description")
                        g_elem = item.find("guid")

                        title = t_elem.text if t_elem is not None and t_elem.text else ""
                        link = l_elem.text if l_elem is not None and l_elem.text else ""
                        desc = d_elem.text if d_elem is not None and d_elem.text else ""
                        guid = g_elem.text if g_elem is not None and g_elem.text else link

                        if title and link:
                            parsed_items.append({
                                "title": title,
                                "link": link,
                                "desc": desc,
                                "guid": guid
                            })
            except Exception as e:
                logger.debug(f"ElementTree parse error ({e}), using regex fallback.")
                parsed_items = self._extract_items_via_regex(xml_text)

            for item in parsed_items:
                title = item["title"]
                desc = item["desc"]
                link = item["link"]
                combined = f"{title} {desc}".lower()

                # Basic relevance check: at least main target keywords present
                if not any(word in combined for word in target_words):
                    continue

                # Extract price
                price_match = re.search(r'\$([0-9,]+(?:\.[0-9]{2})?)', f"{title} {desc}")
                price = self.clean_price(price_match.group(1)) if price_match else None

                if not price or price < 100:
                    continue

                # Detect merchant source
                source = "Deal Aggregator"
                if "apple" in combined:
                    source = "Apple Refurbished"
                elif "best buy" in combined:
                    source = "Best Buy"
                elif "amazon" in combined:
                    source = "Amazon Renewed"
                elif "b&h" in combined or "bhphoto" in combined:
                    source = "B&H Photo"
                elif "ebay" in combined:
                    source = "eBay Refurbished"
                elif "back market" in combined:
                    source = "Back Market"

                unique_id = item["guid"].split("/")[-1] or link.split("/")[-1] or title[:30]
                deal_id = self.generate_deal_id(source, unique_id)

                listings.append(RawListing(
                    id=deal_id,
                    source=source,
                    title=title,
                    price=price,
                    url=link,
                    condition="Refurbished / Open-Box Deal",
                    raw_specs=f"{title} {desc}",
                    category=config.CATEGORY
                ))

        logger.info(f"[{self.name}] Completed: {len(listings)} deals collected.")
        return listings
