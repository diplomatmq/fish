import logging
import os
import subprocess
import sys
from bot import main as bot_main

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("Launcher")

def start_webapp_process() -> subprocess.Popen:
    """Start WebApp in a dedicated Python process."""
    cmd = [sys.executable, "-m", "webapp.app"]
    env = os.environ.copy()
    logger.info("Starting WebApp via subprocess: %s", " ".join(cmd))
    return subprocess.Popen(cmd, env=env)

def main():
    if os.getenv("BOT_USE_WEBHOOK", "1") != "0":
        raise RuntimeError(
            "SERVICE_MODE=all cannot run bot webhook and WebApp on one Railway public port. "
            "Create two Railway services from the same repo: one with SERVICE_MODE=bot for the Telegram webhook, "
            "and one with SERVICE_MODE=webapp for the Mini App. "
            "The bot uses WEBAPP_URL/APP_DOMAIN as WEBHOOK_URL fallback automatically."
        )
    logger.info("🚀 Starting FishBot Unified Launcher (Bot + WebApp)...")

    # Keep WebApp and Bot isolated so web traffic does not starve bot polling.
    webapp_process = start_webapp_process()
    logger.info("WebApp process started (pid=%s)", webapp_process.pid)

    try:
        # IMPORTANT: python-telegram-bot polling must run in the main thread.
        logger.info("Starting Bot...")
        bot_main()
    finally:
        if webapp_process.poll() is None:
            logger.info("Stopping WebApp process...")
            webapp_process.terminate()
            try:
                webapp_process.wait(timeout=10)
            except Exception:
                logger.warning("WebApp process did not stop gracefully")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Stopping...")
