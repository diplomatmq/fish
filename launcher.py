import logging
import os
import subprocess
import sys
import time

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("Launcher")


def _public_base_url() -> str:
    raw = (
        os.getenv("WEBHOOK_URL")
        or os.getenv("WEBAPP_URL")
        or os.getenv("RAILWAY_PUBLIC_DOMAIN")
        or os.getenv("APP_DOMAIN")
        or ""
    ).strip().rstrip("/")
    if raw and not raw.startswith(("http://", "https://")):
        raw = f"https://{raw.lstrip('/')}"
    return raw


def start_bot_process() -> subprocess.Popen:
    """Start PTB webhook server on an internal localhost port."""
    env = os.environ.copy()
    webhook_path = env.get("WEBHOOK_PATH") or "telegram-webhook"
    internal_port = env.get("BOT_INTERNAL_WEBHOOK_PORT") or "9000"

    env["BOT_USE_WEBHOOK"] = "1"
    env["WEBHOOK_LISTEN"] = "127.0.0.1"
    env["WEBHOOK_PORT"] = internal_port
    env["WEBHOOK_PATH"] = webhook_path
    env["BOT_INTERNAL_WEBHOOK_URL"] = f"http://127.0.0.1:{internal_port}/{webhook_path}"

    public_url = _public_base_url()
    if public_url:
        env["WEBHOOK_URL"] = public_url

    cmd = [sys.executable, "-u", "bot.py"]
    logger.info(
        "Starting Bot webhook server: internal=%s public=%s/%s",
        env["BOT_INTERNAL_WEBHOOK_URL"],
        env.get("WEBHOOK_URL", ""),
        webhook_path,
    )
    return subprocess.Popen(cmd, env=env)


def start_webapp_process() -> subprocess.Popen:
    """Start WebApp on Railway public port."""
    env = os.environ.copy()
    webhook_path = env.get("WEBHOOK_PATH") or "telegram-webhook"
    internal_port = env.get("BOT_INTERNAL_WEBHOOK_PORT") or "9000"
    host = env.get("APP_HOST") or "0.0.0.0"
    port = env.get("PORT") or env.get("APP_PORT") or "8080"
    workers = env.get("GUNICORN_WORKERS") or "4"
    timeout = env.get("GUNICORN_TIMEOUT") or "120"
    env["WEBHOOK_PATH"] = webhook_path
    env["BOT_INTERNAL_WEBHOOK_URL"] = f"http://127.0.0.1:{internal_port}/{webhook_path}"

    cmd = [
        "gunicorn",
        "-w",
        workers,
        "-b",
        f"{host}:{port}",
        "webapp.app:app",
        "--timeout",
        timeout,
        "--access-logfile",
        "-",
        "--error-logfile",
        "-",
    ]
    logger.info("Starting WebApp via subprocess: %s", " ".join(cmd))
    return subprocess.Popen(cmd, env=env)


def main():
    logger.info("Starting FishBot unified launcher: public WebApp + proxied Telegram webhook")

    bot_process = start_bot_process()
    logger.info("Bot process started (pid=%s)", bot_process.pid)

    webapp_process = start_webapp_process()
    logger.info("WebApp process started (pid=%s)", webapp_process.pid)

    try:
        while True:
            bot_code = bot_process.poll()
            webapp_code = webapp_process.poll()
            if bot_code is not None:
                raise RuntimeError(f"Bot process exited with code {bot_code}")
            if webapp_code is not None:
                raise RuntimeError(f"WebApp process exited with code {webapp_code}")
            time.sleep(5)
    finally:
        for process, name in ((webapp_process, "WebApp"), (bot_process, "Bot")):
            if process.poll() is None:
                logger.info("Stopping %s process...", name)
                process.terminate()
                try:
                    process.wait(timeout=10)
                except Exception:
                    logger.warning("%s process did not stop gracefully", name)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Stopping...")
