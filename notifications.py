import sqlite3
import time
import json
import asyncio
import logging
from typing import Any, Dict
from pathlib import Path
from config import DB_PATH
from telegram.error import RetryAfter, BadRequest

logger = logging.getLogger(__name__)

NOTIFICATIONS_TABLE = "notifications_queue"

def init_notifications_table():
    path = str(DB_PATH)
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {NOTIFICATIONS_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                method TEXT NOT NULL,
                kwargs TEXT NOT NULL,
                attempts INTEGER DEFAULT 0,
                next_try INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()

async def enqueue_notification(method: str, kwargs: Dict[str, Any], delay_seconds: int = 0):
    """Добавить уведомление в очередь. `kwargs` сериализуются в JSON. Для файлов используйте ключ `document_path`."""
    path = str(DB_PATH)
    next_try = int(time.time()) + int(delay_seconds)
    created_at = int(time.time())
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute(f"INSERT INTO {NOTIFICATIONS_TABLE} (method, kwargs, attempts, next_try, created_at) VALUES (?, ?, 0, ?, ?)",
                    (method, json.dumps(kwargs, ensure_ascii=False), next_try, created_at))
        conn.commit()
    finally:
        conn.close()

async def start_worker(application, poll_interval: float = 1.0):
    """Запустить фоновую задачу-воркер для отправки уведомлений."""
    loop = asyncio.get_event_loop()
    loop.create_task(_worker(application, poll_interval))

async def _worker(application, poll_interval: float):
    path = str(DB_PATH)
    while True:
        try:
            now = int(time.time())
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            cur.execute(f"SELECT id, method, kwargs, attempts FROM {NOTIFICATIONS_TABLE} WHERE next_try <= ? ORDER BY created_at LIMIT 10", (now,))
            rows = cur.fetchall()
            conn.close()

            if not rows:
                await asyncio.sleep(poll_interval)
                continue

            for row in rows:
                nid, method, kwargs_json, attempts = row
                try:
                    kwargs = json.loads(kwargs_json)
                except Exception:
                    logger.exception("Invalid kwargs in notification %s, deleting", nid)
                    _delete_notification(nid)
                    continue

                try:
                    # Special handling for document path
                    if method == 'send_document' and 'document_path' in kwargs:
                        doc_path = kwargs.pop('document_path')
                        # ensure file exists
                        if not Path(doc_path).exists():
                            logger.error("Document not found for notification %s: %s", nid, doc_path)
                            _delete_notification(nid)
                            continue

                        with open(doc_path, 'rb') as f:
                            await application.bot.send_document(**{**kwargs, 'document': f})
                    else:
                        func = getattr(application.bot, method, None)
                        if not func:
                            logger.error("Unknown bot method for notification %s: %s", nid, method)
                            _delete_notification(nid)
                            continue
                        try:
                            await func(**kwargs)
                        except BadRequest as bre:
                            # Try fallback: if entities parsing failed, resend as plain text
                            msg = str(bre)
                            logger.warning("BadRequest while sending notification %s: %s", nid, msg)
                            if "Can't parse entities" in msg or "unexpected end of name token" in msg:
                                # attempt to resend without parse_mode (plain text)
                                fallback_kwargs = dict(kwargs)
                                fallback_kwargs.pop('parse_mode', None)
                                try:
                                    await func(**fallback_kwargs)
                                except Exception as e2:
                                    logger.exception("Fallback send failed for notification %s: %s", nid, e2)
                                    raise
                            else:
                                raise

                    # success -> delete
                    _delete_notification(nid)
                except RetryAfter as e:
                    wait = getattr(e, 'retry_after', None) or 1
                    attempts_next = attempts + 1
                    next_try = int(time.time()) + int(wait) + 1
                    await _reschedule_notification(nid, attempts_next, next_try)
                    logger.warning("RetryAfter for notification %s, retrying in %s sec", nid, wait)
                except Exception as e:
                    # non-retryable error: exponential backoff
                    attempts_next = attempts + 1
                    backoff = min(3600, 2 ** attempts_next)
                    next_try = int(time.time()) + backoff
                    await _reschedule_notification(nid, attempts_next, next_try)
                    logger.exception("Error sending notification %s, rescheduled (attempt %s)", nid, attempts_next)

        except Exception as e:
            logger.exception("Notifications worker critical error: %s", e)
            await asyncio.sleep(5)

async def _reschedule_notification(nid: int, attempts: int, next_try: int):
    path = str(DB_PATH)
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute(f"UPDATE {NOTIFICATIONS_TABLE} SET attempts = ?, next_try = ? WHERE id = ?", (attempts, next_try, nid))
        conn.commit()
    finally:
        conn.close()

def _delete_notification(nid: int):
    path = str(DB_PATH)
    conn = sqlite3.connect(path)
    try:
        cur = conn.cursor()
        cur.execute(f"DELETE FROM {NOTIFICATIONS_TABLE} WHERE id = ?", (nid,))
        conn.commit()
    finally:
        conn.close()
