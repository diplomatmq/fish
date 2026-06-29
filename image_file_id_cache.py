"""Persistent Telegram document file_id cache for catch images."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Dict, Iterable, Optional, Set

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent


def resolve_cache_path() -> Path:
    explicit = os.getenv("IMAGE_FILE_ID_CACHE_PATH", "").strip()
    if explicit:
        return Path(explicit)
    data_dir = Path("/data")
    if data_dir.is_dir():
        return data_dir / "image_file_ids.json"
    db_path = os.getenv("FISHBOT_DB_PATH", "").strip()
    if db_path:
        return Path(db_path).resolve().parent / "image_file_ids.json"
    return PROJECT_ROOT / "image_file_ids.json"


def normalize_cache_key(path: Path | str, base_dir: Path | None = None) -> str:
    """Stable relative key (e.g. crucian.webp) for portability across restarts."""
    base = base_dir or PROJECT_ROOT
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(base.resolve()).as_posix()
        except ValueError:
            return candidate.name
    return candidate.as_posix().lstrip("./")


def collect_catch_image_paths(base_dir: Path | None = None) -> Set[str]:
    """All unique image filenames used for fish/trash/treasure catches."""
    from fish_stickers import FISH_STICKERS
    from trash_stickers import TRASH_STICKERS
    from treasures_stickers import TREASURES_STICKERS

    root = base_dir or PROJECT_ROOT
    keys: Set[str] = set()

    for filename in FISH_STICKERS.values():
        keys.add(normalize_cache_key(filename, root))
    for filename in TRASH_STICKERS.values():
        keys.add(normalize_cache_key(filename, root))
    for filenames in TREASURES_STICKERS.values():
        items = filenames if isinstance(filenames, list) else [filenames]
        for filename in items:
            keys.add(normalize_cache_key(filename, root))

    return keys


def resolve_image_path(cache_key: str, base_dir: Path | None = None) -> Path:
    root = base_dir or PROJECT_ROOT
    return (root / cache_key).resolve()


class ImageFileIdCache:
    def __init__(self, cache_path: Path | None = None, base_dir: Path | None = None) -> None:
        self.cache_path = cache_path or resolve_cache_path()
        self.base_dir = base_dir or PROJECT_ROOT
        self._entries: Dict[str, str] = {}
        self._lock = asyncio.Lock()
        self._dirty = False

    def load(self) -> int:
        if not self.cache_path.exists():
            return 0
        try:
            raw = self.cache_path.read_text(encoding="utf-8")
            data = json.loads(raw) if raw.strip() else {}
        except Exception:
            logger.exception("Failed to load image file_id cache from %s", self.cache_path)
            return 0

        if not isinstance(data, dict):
            return 0

        loaded = 0
        for key, file_id in data.items():
            if not isinstance(key, str) or not isinstance(file_id, str) or not file_id:
                continue
            normalized = normalize_cache_key(key, self.base_dir)
            self._entries[normalized] = file_id
            loaded += 1
        logger.info("Loaded %s image file_id entries from %s", loaded, self.cache_path)
        return loaded

    def get(self, cache_key: str) -> Optional[str]:
        normalized = normalize_cache_key(cache_key, self.base_dir)
        return self._entries.get(normalized)

    def set(self, cache_key: str, file_id: str) -> None:
        if not file_id:
            return
        normalized = normalize_cache_key(cache_key, self.base_dir)
        if self._entries.get(normalized) == file_id:
            return
        self._entries[normalized] = file_id
        self._dirty = True

    def pop(self, cache_key: str) -> None:
        normalized = normalize_cache_key(cache_key, self.base_dir)
        if normalized in self._entries:
            self._entries.pop(normalized, None)
            self._dirty = True

    def missing_keys(self, keys: Iterable[str]) -> list[str]:
        missing = []
        for key in keys:
            normalized = normalize_cache_key(key, self.base_dir)
            path = resolve_image_path(normalized, self.base_dir)
            if not path.exists():
                continue
            if not self.get(normalized):
                missing.append(normalized)
        return missing

    def __len__(self) -> int:
        return len(self._entries)

    async def save_if_dirty(self) -> None:
        async with self._lock:
            if not self._dirty:
                return
            await asyncio.to_thread(self._save_sync)
            self._dirty = False

    def _save_sync(self) -> None:
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = self.cache_path.with_suffix(".tmp")
            tmp_path.write_text(
                json.dumps(self._entries, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            tmp_path.replace(self.cache_path)
        except Exception:
            logger.exception("Failed to save image file_id cache to %s", self.cache_path)
