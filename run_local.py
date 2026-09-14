"""Local runner to test the deal scan cycle without AWS Lambda."""
import os
import sys

# Ensure current directory is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from src.main import run_deal_cycle

if __name__ == "__main__":
    print("🚀 Starting local shopping deal agent cycle...")
    stats = run_deal_cycle()
    print("\n🏁 Deal cycle finished!")
    print(f"Summary: {stats}")
