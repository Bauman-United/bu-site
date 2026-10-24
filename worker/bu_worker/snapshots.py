import gzip
import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path

_RUN = re.compile(r"\d{4}-\d{2}-\d{2}-\d{4}")


def save(
    root: Path, source: str, name: str, body: str, now: datetime, suffix: str = "html"
) -> Path:
    folder = root / source / now.strftime("%Y-%m-%d-%H%M")
    folder.mkdir(parents=True, exist_ok=True)
    # Снимки нужны только для разбора сломавшегося парсинга; gzip ужимает HTML ~в 10 раз.
    path = folder / f"{name}.{suffix}.gz"
    path.write_bytes(gzip.compress(body.encode("utf-8"), compresslevel=6))
    return path


def prune(root: Path, keep_days: int, now: datetime) -> int:
    cutoff = (now - timedelta(days=keep_days)).strftime("%Y-%m-%d")
    removed = 0
    for folder in sorted(root.rglob("*")):
        if (
            folder.exists()
            and folder.is_dir()
            and _RUN.fullmatch(folder.name)
            and folder.name[:10] < cutoff
        ):
            shutil.rmtree(folder)
            removed += 1
    return removed
