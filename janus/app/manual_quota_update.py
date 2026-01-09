import logging
import os
import sys

# Setup path to import app
# In Docker, this file is at /app/app/manual_quota_update.py
# We want to add /app to sys.path so we can do 'from app.core...'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("manual_quota_update")

try:
    from app.core.llm.gemini_quota import GeminiQuotaFetcher

    logger.info("Starting manual Gemini quota update...")

    # Initialize fetcher
    # Note: It will use GOOGLE_APPLICATION_CREDENTIALS env var or default path
    fetcher = GeminiQuotaFetcher()

    # Fetch
    fetcher.fetch_and_update_limits()

    logger.info("Manual update finished.")

except Exception as e:
    logger.error(f"Failed: {e}", exc_info=True)
    sys.exit(1)
