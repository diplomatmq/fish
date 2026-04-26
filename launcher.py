import asyncio
import logging
import os
import threading
from bot import main as bot_main
from webapp.app import app as flask_app

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("Launcher")

def run_flask():
    """Run Flask in a separate thread."""
    port = int(os.getenv("PORT") or os.getenv("APP_PORT", "8008"))
    host = os.getenv("APP_HOST", "0.0.0.0")
    logger.info(f"Starting WebApp on {host}:{port}...")
    flask_app.run(host=host, port=port, debug=False, use_reloader=False)

async def run_bot():
    """Run the bot main function."""
    logger.info("Starting Bot...")
    # Since bot_main calls run_polling(), it is a blocking call.
    # We run it in the main loop or a thread? 
    # Better to run it in a thread if we want true async with other tasks.
    # But python-telegram-bot v20 is async, so we should ideally call its async methods.
    # However, bot_main() is already structured to run the whole app.
    await asyncio.to_thread(bot_main)

async def main():
    logger.info("🚀 Starting FishBot Unified Launcher (Bot + WebApp)...")
    
    # Run Flask in a background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Run Bot in the main event loop (via thread because bot_main is blocking)
    await run_bot()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Stopping...")
