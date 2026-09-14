"""Scraper registry for the extensible shopping deal agent."""
from typing import List
from src.scrapers.base import BaseScraper
from src.scrapers.aggregator import DealAggregatorScraper
from src.scrapers.apple import AppleRefurbishedScraper
from src.scrapers.bestbuy import BestBuyScraper
from src.scrapers.amazon import AmazonRenewedScraper
from src.scrapers.backmarket import BackMarketScraper
from src.scrapers.ebay import EbayRefurbishedScraper
from src.scrapers.bhphoto import BHPhotoScraper

def get_all_scrapers() -> List[BaseScraper]:
    """Returns initialized instances of all active retail and feed scrapers."""
    return [
        DealAggregatorScraper(),
        AppleRefurbishedScraper(),
        BestBuyScraper(),
        AmazonRenewedScraper(),
        BackMarketScraper(),
        EbayRefurbishedScraper(),
        BHPhotoScraper()
    ]

__all__ = [
    "BaseScraper",
    "DealAggregatorScraper",
    "AppleRefurbishedScraper",
    "BestBuyScraper",
    "AmazonRenewedScraper",
    "BackMarketScraper",
    "EbayRefurbishedScraper",
    "BHPhotoScraper",
    "get_all_scrapers"
]
