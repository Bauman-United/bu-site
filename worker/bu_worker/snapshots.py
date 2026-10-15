import shutil
from datetime import datetime, timedelta
from pathlib import Path


def save(root: Path, source: str, name: str, html: str, now: datetime) -> Path:
    folder = root / source / now.strftime("%Y-%m-%d-%H%M")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.html"
    path.write_text(html, encoding="utf-8")
    return path


def prune(root: Path, keep_days: int, now: datetime) -> int:
    cutoff = (now - timedelta(days=keep_days)).strftime("%Y-%m-%d")
    removed = 0
    for folder in root.glob("*/*"):
        if folder.is_dir() and folder.name[:10] < cutoff:
            shutil.rmtree(folder)
            removed += 1
    return removed
