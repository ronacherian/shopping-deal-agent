"""Main orchestration entrypoint for the extensible shopping deal agent."""
import logging
import sys
from typing import Dict, Any, List
from src.config import config
from src.models import RawListing, ParsedDeal
from src.db import DealTracker
from src.matcher import DealMatcher
from src.notifier import EmailNotifier
from src.scrapers import get_all_scrapers

logging.basicConfig(
    level=logging.DEBUG if config.DEBUG else logging.INFO,
    format="[%(levelname)s]\t%(asctime)s\t%(message)s"
)
logger = logging.getLogger(__name__)

def run_deal_cycle() -> Dict[str, Any]:
    """Executes a complete scrape, parse, match, store, and notification cycle."""
    logger.info(f"=== Starting {config.TARGET_PRODUCT} Deal Scan Cycle ===")
    logger.info(f"Target Criteria: M{config.MIN_CHIP_GEN}+ | >={config.MIN_RAM_GB}GB RAM | >={config.MIN_STORAGE_GB}GB SSD | <${config.MAX_PRICE}")

    tracker = DealTracker()
    matcher = DealMatcher()
    notifier = EmailNotifier()

    # 1. Scrape all configured sources
    all_listings: List[RawListing] = []
    seen_ids = set()

    scrapers = get_all_scrapers()
    for scraper in scrapers:
        try:
            listings = scraper.scrape()
            for item in listings:
                if item.id not in seen_ids:
                    seen_ids.add(item.id)
                    all_listings.append(item)
        except Exception as e:
            logger.error(f"Error running scraper {scraper.name}: {e}")

    logger.info(f"==> Total raw listings collected: {len(all_listings)}")

    # 2. Store all discovered listings in DynamoDB for full visibility
    if all_listings:
        tracker.store_all_listings(all_listings)

    # 3. Match and filter listings against target criteria
    matching_deals: List[ParsedDeal] = []
    for item in all_listings:
        is_match, parsed = matcher.fast_filter(item)
        if is_match and parsed:
            logger.info(f"Criteria match detected: {parsed.title} (${parsed.price})")
            verified = matcher.verify_with_gemini(parsed)
            if verified.is_match:
                matching_deals.append(verified)

    logger.info(f"==> Listings strictly matching target criteria: {len(matching_deals)}")

    # 4. Check initial baseline report status
    if not tracker.has_sent_initial_report():
        logger.info("==> Initial confirmation baseline email has not been sent yet. Sending now...")
        deals_to_show = matching_deals
        if not deals_to_show and all_listings:
            deals_to_show = [
                ParsedDeal(
                    id=item.id,
                    source=item.source,
                    title=item.title,
                    price=item.price,
                    url=item.url,
                    chip=f"{config.TARGET_PRODUCT} Deal",
                    ram_gb=16,
                    storage_gb=512,
                    condition=item.condition,
                    gemini_analysis="Discovered during baseline scan. Live monitoring is active."
                )
                for item in all_listings[:5]
            ]
        if deals_to_show:
            sent = notifier.send_alert(deals_to_show, is_baseline=True)
            if sent:
                tracker.mark_initial_report_sent()
        else:
            logger.info("No listings found on baseline scan to display.")

    # 5. Alert for criteria-matching deals (Silent Mode for duplicates)
    deals_to_alert: List[ParsedDeal] = []
    for deal in matching_deals:
        if tracker.should_alert(deal):
            deals_to_alert.append(deal)

    if deals_to_alert:
        logger.info(f"==> Sending alerts for {len(deals_to_alert)} matching deal(s)...")
        sent = notifier.send_alert(deals_to_alert, is_baseline=False)
        if sent:
            for deal in deals_to_alert:
                tracker.record_deal(deal)
    else:
        logger.info("==> No new criteria alerts to dispatch (Silent Mode active).")

    return {
        "status": "success",
        "total_scraped": len(all_listings),
        "matching_criteria": len(matching_deals),
        "alerted": len(deals_to_alert)
    }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler triggered on schedule by EventBridge."""
    trigger_source = event.get("source", "manual-or-test")
    logger.info(f"Lambda triggered by EventBridge: {trigger_source}")
    result = run_deal_cycle()
    return {
        "statusCode": 200,
        "body": result
    }

if __name__ == "__main__":
    result = run_deal_cycle()
    print(f"Cycle finished: {result}")
