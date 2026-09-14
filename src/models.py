"""Data models for the extensible shopping deal agent."""
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
import json

@dataclass
class RawListing:
    """Represents an unprocessed product listing from any marketplace scraper or feed."""
    id: str
    source: str
    title: str
    price: float
    url: str
    condition: str = "Refurbished"
    raw_specs: str = ""
    image_url: Optional[str] = None
    original_price: Optional[float] = None
    category: str = "Laptops"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class ParsedDeal:
    """Represents a validated deal with extracted specifications."""
    id: str
    source: str
    title: str
    price: float
    url: str
    chip: str = ""  # e.g., 'M3 Pro', 'M3 Max', 'M4'
    ram_gb: int = 0  # e.g., 24, 36, 48
    storage_gb: int = 0  # e.g., 1000 (1TB), 2000 (2TB)
    screen_size: str = '14"'
    condition: str = "Refurbished"
    category: str = "Laptops"
    is_match: bool = True
    original_price: Optional[float] = None
    image_url: Optional[str] = None
    gemini_analysis: str = ""
    deal_score: int = 8  # 1 to 10 rating
    extra_specs: Dict[str, Any] = field(default_factory=dict)

    @property
    def savings(self) -> Optional[float]:
        if self.original_price and self.original_price > self.price:
            return round(self.original_price - self.price, 2)
        return None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
