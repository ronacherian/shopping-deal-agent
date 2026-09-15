"""Hybrid regex and Gemini Flash AI deal verification and matcher."""
import re
import json
import logging
import urllib.request
import urllib.error
from typing import Optional, Tuple
from src.config import config
from src.models import RawListing, ParsedDeal

logger = logging.getLogger(__name__)

DISQUALIFIED_KEYWORDS = [
    "case", "cover", "sleeve", "bag", "charger", "power adapter",
    "screen protector", "keyboard skin", "logic board", "motherboard",
    "box only", "parts only", "for parts", "not working", "icloud locked",
    "broken screen", "water damage", "bad board", "shell only"
]

class DealMatcher:
    def __init__(self):
        self.gemini_api_key = config.GEMINI_API_KEY
        self.max_price = config.MAX_PRICE
        self.min_ram = config.MIN_RAM_GB
        self.min_storage = config.MIN_STORAGE_GB

    def fast_filter(self, listing: RawListing) -> Tuple[bool, Optional[ParsedDeal]]:
        """
        Phase 1: Deterministic regex and rule-based filter.
        Quickly weeds out non-matches without consuming AI quota.
        """
        title = listing.title.lower()
        text = f"{title} {listing.raw_specs.lower()}"

        # 1. Price check
        if listing.price is None or listing.price >= self.max_price or listing.price < 500:
            return False, None

        # 2. Check for disqualified accessory / broken item keywords
        for keyword in DISQUALIFIED_KEYWORDS:
            if keyword in text:
                return False, None

        # 3. Target product check: Supports MacBook Pro and MacBook Air
        is_macbook = any(k in text for k in ["macbook pro", "mbp", "macbook air", "mba", "macbook"])
        if not is_macbook:
            return False, None

        # 4. Chip verification: Must be M3 or better (M3, M3 Pro, M3 Max, M4, M4 Pro, M4 Max)
        if any(bad_chip in text for bad_chip in ["m1", "m2", "intel", "i7", "i9", "core i"]):
            if re.search(r'\b(m1|m2)\s*(pro|max|ultra)?\b', text) and not re.search(r'\b(m3|m4)\s*(pro|max)?\b', text):
                return False, None

        chip_match = re.search(r'\b(m4\s*(?:pro|max)?|m3\s*(?:pro|max)?)\b', text, re.IGNORECASE)
        if not chip_match:
            return False, None
        chip = chip_match.group(1).title()

        # 5. RAM verification: >= 24GB
        ram_gb = None
        explicit_ram = re.search(r'(\d+)\s*(?:gb|gig)\s*(?:unified\s*memory|ram|memory)', text)
        if explicit_ram:
            ram_gb = int(explicit_ram.group(1))
        else:
            ram_candidates = re.findall(r'\b(24|32|36|48|64|96|128)\s*(?:gb)?\b', text)
            valid_ram = [int(c) for c in ram_candidates if int(c) not in (13, 14, 15, 16, 512, 1000)]
            if valid_ram:
                ram_gb = max(valid_ram)

        low_ram_match = re.search(r'\b(8|16|18)\s*(?:gb|gig)\s*(?:unified\s*memory|ram|memory)\b', text)
        if low_ram_match:
            return False, None

        if not ram_gb or ram_gb < self.min_ram:
            return False, None

        # 6. Storage verification: >= 1TB (1000GB)
        storage_gb = None
        tb_match = re.search(r'\b([1-8])\s*(?:tb|terabyte)\s*(?:ssd|storage)?\b', text)
        if tb_match:
            storage_gb = int(tb_match.group(1)) * 1000
        else:
            gb_ssd_match = re.search(r'\b(1000|2000|4000)\s*(?:gb|gig)\s*(?:ssd|storage)?\b', text)
            if gb_ssd_match:
                storage_gb = int(gb_ssd_match.group(1))

        low_storage_match = re.search(r'\b(256|512)\s*(?:gb|gig)\s*(?:ssd|storage)\b', text)
        if low_storage_match and not tb_match:
            return False, None

        if not storage_gb or storage_gb < self.min_storage:
            return False, None

        # 7. Screen size detection (13", 14", 15", 16")
        screen_size = '14"'
        if '16' in text and ('16-inch' in text or '16"' in text or '16 in' in text or '16 inch' in text):
            screen_size = '16"'
        elif '15' in text and ('15-inch' in text or '15"' in text or '15 in' in text or '15 inch' in text):
            screen_size = '15"'
        elif '13' in text and ('13-inch' in text or '13"' in text or '13 in' in text or '13 inch' in text or '13.6' in text):
            screen_size = '13"'

        parsed_deal = ParsedDeal(
            id=listing.id,
            source=listing.source,
            title=listing.title,
            price=listing.price,
            url=listing.url,
            chip=chip,
            ram_gb=ram_gb,
            storage_gb=storage_gb,
            screen_size=screen_size,
            condition=listing.condition,
            original_price=listing.original_price,
            image_url=listing.image_url,
            gemini_analysis=f"Verified specs: {chip}, {ram_gb}GB Unified Memory, {storage_gb//1000}TB SSD, {screen_size} display."
        )
        return True, parsed_deal

    def verify_with_gemini(self, deal: ParsedDeal) -> ParsedDeal:
        """Phase 2: Gemini Flash AI verification and deal valuation."""
        if not self.gemini_api_key:
            deal.deal_score = 8
            return deal

        prompt = f"""
Analyze this refurbished MacBook listing (MacBook Pro or MacBook Air) and confirm if it strictly satisfies the target criteria.

Target Criteria:
- Model: Apple MacBook Pro or Apple MacBook Air (Laptop only, no accessories)
- Processor: M3 or better (M3, M3 Pro, M3 Max, M4, M4 Pro, M4 Max)
- RAM / Unified Memory: At least 24GB
- Storage: At least 1TB SSD
- Price: Under $1,990 USD
- Condition: Functioning refurbished or open-box

Listing Details:
- Title: {deal.title}
- Source: {deal.source}
- Price: ${deal.price}
- Stated Condition: {deal.condition}

Respond strictly in valid JSON:
{{
  "is_match": true or false,
  "chip": "string (e.g., M3 or M3 Pro)",
  "ram_gb": integer,
  "storage_gb": integer,
  "condition_summary": "string",
  "deal_score": integer from 1 to 10,
  "analysis": "A concise 2-sentence summary of why this is a great deal and any key notes for the buyer."
}}
"""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent?key={self.gemini_api_key}"
            req_data = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.1,
                    "responseMimeType": "application/json"
                }
            }
            req_body = json.dumps(req_data).encode("utf-8")
            req = urllib.request.Request(url, data=req_body, headers={"Content-Type": "application/json"})

            with urllib.request.urlopen(req, timeout=20) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                candidates = result.get("candidates", [])
                if candidates:
                    content_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                    ai_json = json.loads(content_text)
                    deal.is_match = ai_json.get("is_match", True)
                    if not deal.is_match:
                        return deal
                    deal.chip = ai_json.get("chip", deal.chip)
                    deal.ram_gb = ai_json.get("ram_gb", deal.ram_gb)
                    deal.storage_gb = ai_json.get("storage_gb", deal.storage_gb)
                    deal.condition = ai_json.get("condition_summary", deal.condition)
                    deal.deal_score = ai_json.get("deal_score", 8)
                    deal.gemini_analysis = ai_json.get("analysis", deal.gemini_analysis)
        except Exception as e:
            logger.warning(f"Gemini verification issue: {e}")

        return deal
