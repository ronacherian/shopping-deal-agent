# 🛍️ Shopping Deal Agent

An extensible, serverless shopping deal tracking and alert agent running on **AWS Lambda** at **$0/month** (Free Tier). 

It automatically monitors major retailers and deal syndication feeds every 6 hours, filters and extracts hardware specifications, verifies listings with **Google Gemini Flash AI**, tracks deal history and price drops in **Amazon DynamoDB**, and delivers instant, responsive email digests via **Resend**.

---

## ✨ Features

- **Extensible Architecture**: Configured by default for **Apple MacBook Pro** deals ($M3+$, $\ge 24\text{GB}$ RAM, $\ge 1\text{TB}$ SSD, $<\$1,990$), but fully extensible to any product, category, or hardware specification via environment variables.
- **Multi-Store Coverage**:
  - Apple Certified Refurbished
  - Best Buy Refurbished / Open-Box
  - Amazon Renewed
  - Back Market
  - eBay Refurbished
  - B&H Photo Used Department
  - Syndication Feeds (Slickdeals & DealNews)
- **Two-Phase Verification**:
  - **Phase 1 (Deterministic Filter)**: Zero-latency regex filtering for RAM, storage, CPU generation, screen size, and anti-accessory disqualifiers.
  - **Phase 2 (Gemini Flash AI)**: Deep verification, valuation scoring (1-10), and concise buying analysis.
- **Smart Deduplication & Silent Mode**:
  - Stores all live catalog listings in **Amazon DynamoDB** with 14-day automatic TTL expiration.
  - Sends a one-time baseline confirmation report upon initial activation.
  - Only sends alert emails when a new criteria match appears or an existing deal drops by at least $10.
- **Resilient Email Dispatch**: Direct Resend API integration with custom User-Agent to bypass Cloudflare security rules.

---

## 📁 Project Structure

```
shopping-deal-agent/
├── src/
│   ├── config.py              # Extensible configuration settings
│   ├── models.py              # RawListing and ParsedDeal dataclasses
│   ├── db.py                  # DynamoDB persistence with local JSON fallback
│   ├── matcher.py             # Regex filter + Gemini Flash verification
│   ├── notifier.py            # Responsive HTML email digest via Resend
│   ├── main.py                # Main orchestration & Lambda handler
│   └── scrapers/
│       ├── base.py            # Base scraper with anti-bot headers
│       ├── aggregator.py      # Slickdeals & DealNews RSS feed scraper
│       ├── apple.py           # Apple Refurbished store scraper
│       ├── bestbuy.py         # Best Buy scraper
│       ├── amazon.py          # Amazon Renewed scraper
│       ├── backmarket.py      # Back Market scraper
│       ├── ebay.py            # eBay Refurbished scraper
│       ├── bhphoto.py         # B&H Photo scraper
│       └── __init__.py        # Scraper registry
├── tests/
│   └── test_matcher.py        # 14 unit tests for filtering & spec parsing
├── Dockerfile                 # AWS Lambda container build
├── template.yaml              # AWS SAM CloudFormation template
├── samconfig.toml             # SAM deployment configuration
├── run_local.py               # Local execution runner
├── test_email_send.py         # Resend email test utility
├── deploy.py                  # One-click deployment script
├── requirements.txt           # Python dependencies
└── .env.example               # Environment variables template
```

---

## 🚀 Quick Start (Local Run)

1. **Clone or navigate to workspace**:
   ```bash
   cd /Users/roncherian/workspace/shopping-deal-agent
   ```

2. **Set up virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure `.env`**:
   ```bash
   cp .env.example .env
   # Edit your RESEND_API_KEY, ALERT_EMAIL_TO, and GEMINI_API_KEY
   ```

4. **Run Unit Tests**:
   ```bash
   python3 -m unittest discover -s tests -p "test_*.py"
   ```

5. **Run a Local Scan Cycle**:
   ```bash
   python3 run_local.py
   ```

---

## ☁️ Deployment to AWS Lambda

The agent deploys as a containerized Lambda function triggered by an EventBridge schedule rule (`rate(6 hours)`).

### Option 1: Using the Deployment Script
```bash
python3 deploy.py
```

### Option 2: Using AWS SAM Directly
```bash
sam build
sam deploy
```

### Testing the Live Lambda Function
```bash
sam remote invoke MacBookDealFinderFunction --stack-name sam-app
```

---

## ⚙️ Configuration Reference

| Variable | Default | Description |
| :--- | :--- | :--- |
| `TARGET_PRODUCT` | `MacBook Pro` | Target product name or query term |
| `CATEGORY` | `Laptops` | Product category |
| `MAX_PRICE` | `1990.0` | Maximum price ceiling in USD |
| `MIN_RAM_GB` | `24` | Minimum RAM in gigabytes |
| `MIN_STORAGE_GB` | `1000` | Minimum SSD storage in gigabytes |
| `MIN_CHIP_GEN` | `3` | Minimum Apple Silicon chip generation |
| `RESEND_API_KEY` | - | Resend API key |
| `ALERT_EMAIL_TO` | - | Destination email address |
| `ALERT_EMAIL_FROM` | `Shopping Deals <onboarding@resend.dev>` | Sender email address |
| `GEMINI_API_KEY` | - | Google AI Studio API key |
| `DYNAMODB_TABLE_NAME` | `MacBookDeals` | DynamoDB table name |
| `DEAL_TTL_DAYS` | `14` | Days before DynamoDB entries expire |
