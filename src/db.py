"""State tracking and deal storage using Amazon DynamoDB and local JSON fallback."""
import os
import json
import time
import logging
from typing import Optional, Dict, Any, List
from src.config import config
from src.models import RawListing, ParsedDeal

logger = logging.getLogger(__name__)

INITIAL_REPORT_FLAG_KEY = "__SYSTEM_INITIAL_REPORT_SENT__"

class DealTracker:
    def __init__(self, table_name: Optional[str] = None, local_file: Optional[str] = None):
        self.table_name = table_name or config.DYNAMODB_TABLE_NAME
        self.local_file = local_file or config.LOCAL_STATE_FILE
        self.dynamo_table = None
        self._init_dynamo()

    def _init_dynamo(self):
        """Attempts to initialize DynamoDB client if running in AWS or credentials exist."""
        try:
            import boto3
            dynamodb = boto3.resource("dynamodb", region_name=config.AWS_REGION)
            table = dynamodb.Table(self.table_name)
            _ = table.table_status
            self.dynamo_table = table
            logger.info(f"Connected to DynamoDB table: {self.table_name}")
        except Exception as e:
            logger.info(f"DynamoDB not available ({e}). Using local file storage: {self.local_file}")
            self.dynamo_table = None

    def _load_local(self) -> Dict[str, Any]:
        if os.path.exists(self.local_file):
            try:
                with open(self.local_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading local state: {e}")
        return {}

    def _save_local(self, data: Dict[str, Any]):
        try:
            with open(self.local_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error writing to local state: {e}")

    def has_sent_initial_report(self) -> bool:
        """Checks if the first confirmation baseline email has already been dispatched."""
        if self.dynamo_table:
            try:
                resp = self.dynamo_table.get_item(Key={"deal_id": INITIAL_REPORT_FLAG_KEY})
                return "Item" in resp
            except Exception as e:
                logger.warning(f"Error checking initial report status in DynamoDB: {e}")

        local_data = self._load_local()
        return INITIAL_REPORT_FLAG_KEY in local_data

    def mark_initial_report_sent(self):
        """Records that the initial baseline email report has been sent."""
        now = int(time.time())
        item_data = {
            "deal_id": INITIAL_REPORT_FLAG_KEY,
            "sent_at": now,
            "ttl": now + (365 * 86400)
        }
        if self.dynamo_table:
            try:
                self.dynamo_table.put_item(Item=item_data)
                return
            except Exception as e:
                logger.warning(f"Error writing initial report flag to DynamoDB: {e}")

        local_data = self._load_local()
        local_data[INITIAL_REPORT_FLAG_KEY] = item_data
        self._save_local(local_data)

    def should_alert(self, deal: ParsedDeal) -> bool:
        """
        Determines if an alert should be sent for a target match.
        Returns True if:
        1. Deal has never had an email alert sent before (no 'alerted_at').
        2. Deal was alerted previously, but price has dropped by at least $10.
        """
        if self.dynamo_table:
            try:
                response = self.dynamo_table.get_item(Key={"deal_id": deal.id})
                item = response.get("Item")
                if not item or "alerted_at" not in item:
                    return True
                prev_price = float(item.get("price", 0))
                if deal.price <= (prev_price - 10.0):
                    logger.info(f"Price drop detected for {deal.id}: ${prev_price} -> ${deal.price}")
                    return True
                return False
            except Exception as e:
                logger.warning(f"DynamoDB lookup error ({e}), falling back to local state")

        local_data = self._load_local()
        item = local_data.get(deal.id)
        if not item or "alerted_at" not in item:
            return True
        prev_price = float(item.get("price", 0))
        if deal.price <= (prev_price - 10.0):
            logger.info(f"Price drop detected for {deal.id}: ${prev_price} -> ${deal.price}")
            return True
        return False

    def store_all_listings(self, listings: List[RawListing]):
        """Stores all discovered raw listings in DynamoDB so the table is populated."""
        now = int(time.time())
        ttl = now + (config.DEAL_TTL_DAYS * 86400)

        stored_count = 0
        local_data = self._load_local() if not self.dynamo_table else {}

        for item in listings:
            existing_alerted = None
            if not self.dynamo_table and item.id in local_data:
                existing_alerted = local_data[item.id].get("alerted_at")

            item_data = {
                "deal_id": item.id,
                "source": item.source,
                "title": item.title,
                "price": str(item.price) if item.price else "0",
                "url": item.url,
                "condition": item.condition or "Refurbished",
                "recorded_at": now,
                "ttl": ttl
            }
            if existing_alerted:
                item_data["alerted_at"] = existing_alerted

            if self.dynamo_table:
                try:
                    self.dynamo_table.put_item(Item=item_data)
                    stored_count += 1
                except Exception as e:
                    logger.debug(f"DynamoDB put item error: {e}")
            else:
                local_data[item.id] = item_data
                stored_count += 1

        if not self.dynamo_table:
            self._save_local(local_data)

        logger.info(f"==> Stored {stored_count} live listings in DynamoDB table '{self.table_name}'.")

    def record_deal(self, deal: ParsedDeal):
        """Records an alerted deal in DynamoDB with alerted_at timestamp and TTL expiration."""
        now = int(time.time())
        ttl = now + (config.DEAL_TTL_DAYS * 86400)
        item_data = {
            "deal_id": deal.id,
            "source": deal.source,
            "title": deal.title,
            "price": str(deal.price),
            "url": deal.url,
            "chip": deal.chip,
            "ram_gb": deal.ram_gb,
            "storage_gb": deal.storage_gb,
            "alerted_at": now,
            "ttl": ttl
        }

        if self.dynamo_table:
            try:
                self.dynamo_table.put_item(Item=item_data)
                return
            except Exception as e:
                logger.warning(f"DynamoDB save error ({e}), saving to local storage")

        local_data = self._load_local()
        local_data[deal.id] = item_data
        self._save_local(local_data)
