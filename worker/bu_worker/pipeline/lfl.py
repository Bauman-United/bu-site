from collections.abc import Callable

from sqlalchemy.orm import Session

from bu_worker.dto import JoinFootballBundle
from bu_worker.pipeline.common import IngestResult
from bu_worker.pipeline.joinfootball import SanityError, sanity_check
from bu_worker.pipeline.joinfootball import ingest as ingest_bundle

SOURCE = "lfl"


def ingest(
    session: Session,
    bundle: JoinFootballBundle,
    our_team_id: str,
    our_names: list[str],
    match_url: Callable[[str], str],
) -> IngestResult:
    return ingest_bundle(
        session,
        bundle,
        our_team_id,
        our_names,
        source=SOURCE,
        match_url=match_url,
    )


__all__ = ["SanityError", "ingest", "sanity_check"]
