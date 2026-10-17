"""Разовая починка данных: «пустышки» игроков, созданные синком content/ на пустой базе.

Старый синк для content/players/<slug>.yaml без имени создавал игрока slug=<slug>,
last_name=<slug>; затем парсер заводил настоящего игрока со slug «<slug>-2».
"""

from dataclasses import dataclass, field

from bu_core.models import Player, PlayerSourceLink
from bu_core.text import player_slug
from sqlalchemy import select
from sqlalchemy.orm import Session

from bu_worker.pipeline.content import apply_pending_player_overrides


@dataclass
class CleanupReport:
    removed: int = 0
    renamed: list[tuple[str, str]] = field(default_factory=list)
    tags: set[str] = field(default_factory=set)


def _is_placeholder(session: Session, p: Player) -> bool:
    if p.first_name or p.last_name != p.slug:
        return False
    linked = session.scalars(
        select(PlayerSourceLink.id).where(PlayerSourceLink.player_id == p.id)
    ).first()
    return linked is None


def fix_placeholder_players(session: Session) -> CleanupReport:
    report = CleanupReport()
    placeholders = [p for p in session.scalars(select(Player)) if _is_placeholder(session, p)]
    freed = {p.slug for p in placeholders}
    for p in placeholders:
        session.delete(p)
        report.removed += 1
    session.flush()

    # Настоящие игроки, получившие «<slug>-N» из-за пустышки, возвращают свой slug.
    for p in session.scalars(select(Player)):
        natural = player_slug(p.first_name, p.last_name)
        if natural in freed and p.slug != natural and p.slug.startswith(f"{natural}-"):
            report.renamed.append((p.slug, natural))
            p.slug = natural
            freed.discard(natural)
    session.flush()

    report.tags = apply_pending_player_overrides(session) | {"players", "home", "stats"}
    report.tags |= {f"player:{new}" for _, new in report.renamed}
    report.tags |= {f"player:{old}" for old, _ in report.renamed}
    return report
