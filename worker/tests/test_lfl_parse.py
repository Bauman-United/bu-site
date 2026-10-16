from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from bu_core.models import Match, MatchEvent, Player, PlayerSourceLink, Tournament
from bu_worker.dto import JoinFootballBundle
from bu_worker.pipeline.lfl import ingest
from bu_worker.sources.lfl.parse import (
    ParseError,
    parse_calendar,
    parse_current_player_ids,
    parse_match,
    parse_players,
    parse_season_id,
    parse_standings,
    parse_tournament_info,
)
from sqlalchemy import select

MSK = ZoneInfo("Europe/Moscow")

TOURNAMENT = """
<div class="league_text">2-й дивизион А ВЛ-2026</div>
<button season_id="84">Показать еще 10</button>
<table class="round_table calendar tournament_table"><tbody>
  <tr><td>1</td><td><img src="/one.png"></td><td>Империя-Д</td>
      <td>25</td><td>20</td><td>3</td><td>2</td><td>140</td><td>57</td><td>83</td><td>63</td></tr>
  <tr><td>3</td><td><img src="/bu.png"></td><td>Бауман Юнайтед</td>
      <td>26</td><td>18</td><td>2</td><td>6</td><td>137</td><td>64</td><td>73</td><td>56</td></tr>
</tbody></table>
"""

SQUAD = """
<table class="round_table stats tournament_squads_table"><tbody>
  <tr><td class="tour-header" colspan="8">Полузащитник</td></tr>
  <tr><td>1</td><td class="FIO"><a class="player" href="/player266203">Королёв Александр</a>
      <span class="amplua">Полузащитник</span></td>
      <td>24</td><td>12</td><td>22</td><td>3</td><td>1</td><td>1</td></tr>
</tbody></table>
"""

CLUB = """
<div class="club-player-list">
  <a href="/player266203">Королёв Александр</a>
  <a href="/player282208">Долженков Артём</a>
</div>
"""

CALENDAR = """
<table class="round_table calendar calendar_result league_tournament_calendar_table"><tbody>
  <tr><td class="separator tour-header" colspan="7">26 тур</td></tr>
  <tr><td><a href="/match924162596">11.10.2026 (вс)</a></td><td>10:00</td>
      <td><a title="Корп Софт" href="/club15167"><img src="/corp.png">Корп Софт</a></td>
      <td><a href="/match924162596">7:1</a></td>
      <td><a title="Бауман Юнайтед" href="/club14270"><img src="/bu.png">Бауман</a></td>
      <td><a href="/stadium763">Аником Арена</a></td>
      <td><a href="/tournament32573">Восток, 2-й дивизион А</a></td></tr>
  <tr><td><a href="/match111">12.10.2026</a></td><td>12:00</td>
      <td><a title="Бауман Юнайтед" href="/club14270">Бауман</a></td><td>1:0</td>
      <td><a title="Докукина" href="/club254">Докукина</a></td><td>-</td>
      <td><a href="/tournament33238">Кубок ВЛ</a></td></tr>
</tbody></table>
"""

MATCH = """
<div class="some_news" id="match924162596">
  <div class="match_team match_team_home"><a href="/club15167">Корп Софт</a></div>
  <div class="match_score">7</div><div class="match_score">:</div><div class="match_score">1</div>
  <div class="match_team match_team_away"><a href="/club14270">Бауман Юнайтед</a></div>
  <div class="match_right">
    <p class="match_right_head">Голы:</p><div class="match_members">
      <p><a class="match_members_club" href="/club15167">Корп Софт</a></p>
      <a href="/player1">Фёдоров Александр (7)</a>
      <p><a class="match_members_club" href="/club14270">Бауман Юнайтед</a></p>
      <a href="/player266203">Королёв Александр (1)</a>
    </div>
    <p class="match_right_head">Предупреждения:</p><div class="match_members">
      <span><a href="/player266203">Королёв Александр <img src="/popup_yc.png"> (</a>
      <a href="/club14270">Бауман Юнайтед</a>, 0');</span>
    </div>
  </div>
</div>
"""


def test_tournament_and_season():
    info = parse_tournament_info(TOURNAMENT, "32573", "https://lfl.ru/tournament32573")
    assert info.name == "2-й дивизион А ВЛ-2026"
    assert (info.period_start, info.period_end) == (date(2026, 7, 1), date(2027, 6, 30))
    assert parse_season_id(TOURNAMENT) == "84"


def test_players():
    current = parse_current_player_ids(CLUB)
    assert current == {"266203", "282208"}
    player = parse_players(SQUAD, current)[0]
    assert player.model_dump() == {
        "external_id": "266203",
        "full_name": "Королёв Александр",
        "number": None,
        "position": "MF",
        "played": 24,
        "goals": 12,
        "assists": 22,
        "yellow": 3,
        "red": 2,
        "active": True,
        "photo_url": None,
    }


def test_calendar_filters_tournament():
    entries = parse_calendar(CALENDAR, "32573")
    assert len(entries) == 1
    entry = entries[0]
    assert entry.kickoff == datetime(2026, 10, 11, 10, 0, tzinfo=MSK)
    assert (entry.home_team_id, entry.away_team_id) == ("15167", "14270")
    assert (entry.home_score, entry.away_score, entry.round) == (7, 1, "26 тур")


def test_standings():
    rows = parse_standings(TOURNAMENT)
    assert len(rows) == 2
    us = rows[1]
    assert (us.pos, us.played, us.gf, us.ga, us.pts) == (3, 26, 137, 64, 56)


def test_match_uses_zero_when_lfl_has_no_minutes():
    detail = parse_match(MATCH)
    assert len([event for event in detail.events if event.type == "goal"]) == 8
    ours = [event for event in detail.events if event.side == "away"]
    assert [(event.type, event.player_name, event.minute) for event in ours] == [
        ("goal", "Королёв Александр", 0),
        ("yellow", "Королёв Александр", 0),
    ]
    assert all(event.note == "минута не указана" for event in detail.events)


def test_broken_html_raises():
    with pytest.raises(ParseError):
        parse_players("<html></html>")
    with pytest.raises(ParseError):
        parse_calendar("<html></html>")


def test_lfl_bundle_ingests_with_its_own_source(db):
    bundle = JoinFootballBundle(
        tournament=parse_tournament_info(TOURNAMENT, "32573", "https://lfl.ru/tournament32573"),
        players=parse_players(SQUAD, parse_current_player_ids(CLUB)),
        calendar=parse_calendar(CALENDAR, "32573"),
        details={"924162596": parse_match(MATCH)},
        standings=parse_standings(TOURNAMENT),
    )
    ingest(
        db,
        bundle,
        "14270",
        ["Бауман Юнайтед"],
        lambda match_id: f"https://lfl.ru/match{match_id}",
    )
    match = db.scalars(select(Match)).one()
    assert (match.source, match.score_us, match.score_them) == ("lfl", 1, 7)
    assert match.source_url == "https://lfl.ru/match924162596"
    assert len(db.scalars(select(MatchEvent)).all()) == 9
    player = db.scalars(select(Player)).one()
    link = db.scalars(select(PlayerSourceLink)).one()
    assert (player.last_name, link.source, link.external_id) == ("Королёв", "lfl", "266203")
    tournament = db.scalars(select(Tournament)).one()
    assert (tournament.source, tournament.kind, tournament.season.slug) == (
        "lfl",
        "league",
        "2026-27",
    )


PLAYERS_LIST = """
<div class="player_logo"><a href="https://lfl.ru/photo/persons/source/217632.jpg">
  <img src="https://lfl.ru/photo/persons/source/217632.jpg" height="110"></a></div>
<div class="player_title"><p class="player_title_name">
  <a href="/person217632">Королёв Александр Дмитриевич</a></p></div>
<div class="player_logo"><a href="x"><img src="https://lfl.ru/photo/persons/source/235393.jpg"></a></div>
<div class="player_title"><p class="player_title_name">
  <a href="/person235393">Моисеев Павел Александрович-//</a></p></div>
<div class="player_logo"></div>
<div class="player_title"><p class="player_title_name">
  <a href="/person1">Безфото Иван Иванович</a></p></div>
"""


def test_player_photos_keyed_by_last_and_first_name():
    from bu_worker.sources.lfl.parse import parse_player_photos

    assert parse_player_photos(PLAYERS_LIST) == {
        "королев александр": "https://lfl.ru/photo/persons/source/217632.jpg",
        "моисеев павел": "https://lfl.ru/photo/persons/source/235393.jpg",
    }


def test_attach_photos_matches_squad_names():
    from bu_worker.dto import ParsedPlayer
    from bu_worker.sources.lfl.parse import attach_photos, parse_player_photos

    def player(ext: str, name: str) -> ParsedPlayer:
        return ParsedPlayer(
            external_id=ext,
            full_name=name,
            number=None,
            position="MF",
            played=1,
            goals=0,
            assists=0,
            yellow=0,
            red=0,
        )

    out = attach_photos(
        [player("266203", "Королёв Александр"), player("9", "Неизвестный Игрок")],
        parse_player_photos(PLAYERS_LIST),
    )
    assert out[0].photo_url == "https://lfl.ru/photo/persons/source/217632.jpg"
    assert out[1].photo_url is None


PERSON_PAGE = """
<div class="player_logo"><a href="https://lfl.ru/photo/persons/source/218695.jpg">
  <img src="https://lfl.ru/photo/persons/source/218695.jpg" height="280"></a></div>
<div class="player_title"><p class="player_title_name">
  <a href="/person218695">Гангелин Максим Юрьевич</a></p></div>
"""


def test_fill_missing_photos_from_player_pages():
    from bu_worker.dto import ParsedPlayer
    from bu_worker.sources.lfl.parse import fill_missing_photos

    def player(ext: str, name: str, photo: str | None) -> ParsedPlayer:
        return ParsedPlayer(
            external_id=ext,
            full_name=name,
            number=None,
            position="MF",
            played=1,
            goals=0,
            assists=0,
            yellow=0,
            red=0,
            photo_url=photo,
        )

    requested: list[str] = []

    def fetch(player_id: str) -> str:
        requested.append(player_id)
        return PERSON_PAGE if player_id == "267515" else "<html>нет фото</html>"

    out = fill_missing_photos(
        [
            player("1", "Королёв Александр", "https://lfl.ru/photo/persons/source/217632.jpg"),
            player("267515", "Гангелин Максим", None),
            player("9", "Неизвестный Игрок", None),
        ],
        fetch,
    )
    assert requested == ["267515", "9"]  # у кого фото уже есть — страницу не запрашиваем
    assert out[1].photo_url == "https://lfl.ru/photo/persons/source/218695.jpg"
    assert out[2].photo_url is None
