"""Automated deployment script for AWS SAM with secure .env parameter injection."""
import os
import sys
import shutil
import subprocess

def load_env(env_path=".env"):
    """Parses key-value pairs from .env without external dependencies."""
    env_vars = {}
    if not os.path.exists(env_path):
        return env_vars
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env_vars[k.strip()] = v.strip().strip('"').strip("'")
    return env_vars

def check_prerequisites():
    if not shutil.which("sam"):
        print("❌ Error: AWS SAM CLI is not installed or not in PATH.")
        print("Install it with: brew install aws-sam-cli")
        sys.exit(1)
    if not shutil.which("docker"):
        print("❌ Error: Docker is not installed or not in PATH.")
        sys.exit(1)

def run_command(cmd, desc):
    print(f"\n⚙️ {desc}...")
    # Hide sensitive parameter overrides in log output
    display_cmd = []
    for arg in cmd:
        if "ResendApiKey" in arg or "GeminiApiKey" in arg:
            display_cmd.append("--parameter-overrides [SECRETS_INJECTED_FROM_ENV]")
        else:
            display_cmd.append(arg)
    print(f"$ {' '.join(display_cmd)}")

    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"❌ Failed: {desc}")
        sys.exit(result.returncode)
    print(f"✅ Success: {desc}")

def main():
    check_prerequisites()
    print("🔒 Validating environment configuration...")
    env_vars = load_env()

    # Fail fast if RESEND_API_KEY is missing
    resend_key = env_vars.get("RESEND_API_KEY", "").strip()
    if not resend_key:
        print("❌ Error: RESEND_API_KEY is missing or empty in .env!")
        print("Please add your key to .env before deploying so deal alerts can be sent.")
        sys.exit(1)

    gemini_key = env_vars.get("GEMINI_API_KEY", "").strip()
    if not gemini_key:
        print("⚠️ Warning: GEMINI_API_KEY not found in .env. Falling back to deterministic regex matcher.")

    email_to = env_vars.get("ALERT_EMAIL_TO", "ronabraham2000@gmail.com")
    email_from = env_vars.get("ALERT_EMAIL_FROM", "Shopping Deals <onboarding@resend.dev>")
    target_product = env_vars.get("TARGET_PRODUCT", "MacBook Pro")
    category = env_vars.get("CATEGORY", "Laptops")
    max_price = env_vars.get("MAX_PRICE", "1990.0")
    min_ram = env_vars.get("MIN_RAM_GB", "24")
    min_storage = env_vars.get("MIN_STORAGE_GB", "1000")

    overrides = [
        f'ResendApiKey="{resend_key}"',
        f'GeminiApiKey="{gemini_key}"',
        f'AlertEmailTo="{email_to}"',
        f'AlertEmailFrom="{email_from}"',
        f'TargetProduct="{target_product}"',
        f'Category="{category}"',
        f'MaxPrice={max_price}',
        f'MinRam={min_ram}',
        f'MinStorage={min_storage}'
    ]

    print("🚀 Starting secure deployment of Shopping Deal Agent to AWS Lambda...")
    run_command(["sam", "build"], "Building containerized SAM application")
    run_command([
        "sam", "deploy",
        "--resolve-s3",
        "--resolve-image-repos",
        "--parameter-overrides", " ".join(overrides)
    ], "Deploying SAM stack with dynamic secret injection")

    print("\n🎉 Deployment complete! The Shopping Deal Agent is live and secured.")

if __name__ == "__main__":
    main()
