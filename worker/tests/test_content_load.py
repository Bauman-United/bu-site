from pathlib import Path

import pytest
from bu_worker.sources.content import ContentError, load_content

REPO_CONTENT = Path(__file__).resolve().parents[2] / "content"


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def minimal(root: Path) -> None:
    write(root, "club.yaml", "name: Бауман Юнайтед\nprimary_tournament: null\n")
    write(root, "history.yaml", "timeline: []\ntrophies: []\nlegends: []\n")
    write(root, "tournaments.yaml", "[]\n")


def test_repo_content_is_valid():
    bundle = load_content(REPO_CONTENT)
    assert bundle.club["name"] == "Бауман Юнайтед"
    assert bundle.news


def test_player_and_news(tmp_path):
    minimal(tmp_path)
    write(
        tmp_path,
        "players/aleksandr-korolev.yaml",
        "first_name: Александр\nlast_name: Королев\nnickname: Король\naliases: [Саня]\n",
    )
    write(
        tmp_path,
        "news/hello.md",
        "---\ndate: 2026-09-06\ntag: match\ntitle: Привет\n---\nТекст **жирный**\n",
    )
    bundle = load_content(tmp_path)
    player = bundle.players["aleksandr-korolev"]
    assert player.nickname == "Король" and player.aliases == ["Саня"]
    assert player.provided_fields() == {"nickname"}
    assert bundle.news[0].slug == "hello" and bundle.news[0].body.startswith("Текст")


def test_invalid_tag_reports_file(tmp_path):
    minimal(tmp_path)
    write(tmp_path, "news/bad.md", "---\ndate: 2026-09-06\ntag: gossip\ntitle: X\n---\n")
    with pytest.raises(ContentError) as err:
        load_content(tmp_path)
    assert "news/bad.md" in str(err.value) and "tag" in str(err.value)


def test_manual_match(tmp_path):
    minimal(tmp_path)
    write(
        tmp_path,
        "tournaments.yaml",
        "- {slug: lfl-2026, name: ЛФЛ 8×8, short: ЛФЛ, kind: league, season: 2026}\n",
    )
    write(
        tmp_path,
        "matches/2026-10-11-energiya.yaml",
        """
tournament: lfl-2026
kickoff: 2026-10-11T14:00:00+03:00
home: true
opponent: {name: Энергия}
status: finished
score: {us: 3, them: 1}
squad: [aleksandr-korolev]
events:
  - {minute: 12, type: goal, team: us, player: aleksandr-korolev}
""",
    )
    match = load_content(tmp_path).matches["2026-10-11-energiya"]
    assert match.score is not None and match.score.us == 3
    assert match.events[0].player == "aleksandr-korolev"


def test_naive_kickoff_is_moscow_time(tmp_path):
    from datetime import timedelta

    minimal(tmp_path)
    write(tmp_path, "matches/x.yaml", "kickoff: 2026-10-20T19:30:00\n")
    kickoff = load_content(tmp_path).matches["x"].kickoff
    assert kickoff is not None and kickoff.utcoffset() == timedelta(hours=3)


def test_tournament_season_is_a_year(tmp_path):
    minimal(tmp_path)
    write(
        tmp_path,
        "tournaments.yaml",
        "- {slug: a, name: A, short: A, season: 2026}\n"
        "- {slug: b, name: B, short: B, season: 2025-26}\n",
    )
    assert [t.season for t in load_content(tmp_path).tournaments] == ["2026", "2025-26"]


def test_tournament_season_garbage_reports_file(tmp_path):
    minimal(tmp_path)
    write(tmp_path, "tournaments.yaml", "- {slug: a, name: A, short: A, season: осень}\n")
    with pytest.raises(ContentError) as err:
        load_content(tmp_path)
    assert "tournaments.yaml" in str(err.value) and "season" in str(err.value)
