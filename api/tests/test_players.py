def test_active_players_ordered_with_season_stats(client):
    players = client.get("/players", params={"active": "true"}).json()
    assert [p["slug"] for p in players] == ["egor-kucha", "aleksandr-korolev"]
    assert players[1]["season"]["goals"] == 2
    assert "birth" not in str(players)


def test_players_can_be_filtered_by_tournament(client):
    players = client.get("/players", params={"tournament": "liga-inzhenerov"}).json()
    assert [p["slug"] for p in players] == ["egor-kucha", "aleksandr-korolev"]
    assert players[1]["season"]["assists"] == 6
    assert client.get("/players", params={"tournament": "unknown"}).json() == []


def test_player_detail(client):
    p = client.get("/players/aleksandr-korolev").json()
    assert p["nickname"] == "Король"
    assert p["total"]["assists"] == 6
    assert p["seasons"][0]["season"] == "2026-27"
    assert set(p["team_best"]) >= {"goals", "assists"}
    assert client.get("/players/nobody").status_code == 404


def test_player_detail_splits_stats_by_tournament(client, db):
    from bu_core.models import Player, PlayerTournamentStats, Season, Tournament
    from bu_core.recompute import recompute
    from sqlalchemy import select

    season = db.scalars(select(Season).where(Season.slug == "2026-27")).one()
    lfl = Tournament(
        slug="2-y-divizion-a",
        name="2-й дивизион А · ВЛ-2026",
        short="2-й дивизион А",
        source="lfl",
        external_id="32573",
        season_id=season.id,
    )
    db.add(lfl)
    db.flush()
    korolev = db.scalars(select(Player).where(Player.slug == "aleksandr-korolev")).one()
    db.add(
        PlayerTournamentStats(
            player_id=korolev.id,
            tournament_id=lfl.id,
            played=24,
            goals=12,
            assists=22,
            yellow=3,
            red=1,
        )
    )
    db.flush()
    recompute(db)

    p = client.get("/players/aleksandr-korolev").json()
    rows = {r["tournament"]["slug"]: r["stats"] for r in p["tournaments"]}
    assert rows["liga-inzhenerov"]["goals"] == 2 and rows["liga-inzhenerov"]["played"] == 5
    assert rows["2-y-divizion-a"]["goals"] == 12 and rows["2-y-divizion-a"]["red"] == 1
    assert p["season"]["goals"] == 14  # общая статистика сезона = сумма турниров
    assert p["tournaments"][0]["season"] == "2026-27"


def test_roster_includes_former_players_who_played_this_season(client, db):
    from bu_core.models import Player, PlayerTournamentStats, Tournament
    from bu_core.recompute import recompute
    from sqlalchemy import select

    t = db.scalars(select(Tournament).where(Tournament.slug == "liga-inzhenerov")).one()
    gone = Player(
        slug="maksim-gangelin",
        first_name="Максим",
        last_name="Гангелин",
        position="MF",
        active=False,
        aliases=[],
        manual_fields=[],
        achievements=[],
    )
    db.add(gone)
    db.flush()
    db.add(PlayerTournamentStats(player_id=gone.id, tournament_id=t.id, played=10, goals=1))
    db.flush()
    recompute(db)

    roster = [p["slug"] for p in client.get("/players", params={"roster": "true"}).json()]
    assert "maksim-gangelin" in roster
    assert "aleksandr-korolev" in roster
    assert "old-boy" not in roster  # отчислен и в этом сезоне не играл
    active = [p["slug"] for p in client.get("/players", params={"active": "true"}).json()]
    assert "maksim-gangelin" not in active
    by_t = client.get("/players", params={"roster": "true", "tournament": "liga-inzhenerov"}).json()
    assert "maksim-gangelin" in [p["slug"] for p in by_t]


def _add_league_tournaments(db):
    """БЛ-кубок и ЛФЛ текущего сезона + БЛ прошлого сезона (не должен попадать в суммы)."""
    from bu_core.models import Player, PlayerTournamentStats, Season, Tournament
    from bu_core.recompute import recompute
    from sqlalchemy import select

    season = db.scalars(select(Season).where(Season.slug == "2026-27")).one()
    old_season = Season(slug="2025-26", label="2025/26")
    cup = Tournament(
        slug="kubok-spec",
        name="Кубок Специалистов · Осень 2026",
        short="Кубок",
        source="joinfootball",
        external_id="1067299",
        season=season,
    )
    lfl = Tournament(
        slug="lfl-8x8",
        name="ЛФЛ 8×8 · 2026/27",
        short="ЛФЛ",
        source="lfl",
        external_id="lfl-1",
        season=season,
    )
    old_bl = Tournament(
        slug="liga-2025",
        name="Лига Инженеров · Весна 2026",
        short="Лига Инженеров",
        source="joinfootball",
        external_id="1000",
        season=old_season,
    )

    def player(slug, active=True):
        return Player(
            slug=slug,
            first_name=slug,
            last_name=slug,
            position="MF",
            active=active,
            aliases=[],
            manual_fields=[],
            achievements=[],
        )

    gone, lfl_only = player("gone", active=False), player("lfl-only")
    db.add_all([old_season, cup, lfl, old_bl, gone, lfl_only])
    db.flush()
    by = {p.slug: p for p in db.scalars(select(Player))}
    db.add_all(
        [
            PlayerTournamentStats(
                player_id=by["aleksandr-korolev"].id, tournament_id=cup.id, played=2, goals=1
            ),
            PlayerTournamentStats(player_id=gone.id, tournament_id=cup.id, played=1),
            PlayerTournamentStats(
                player_id=by["aleksandr-korolev"].id,
                tournament_id=lfl.id,
                played=3,
                goals=4,
                yellow=1,
            ),
            PlayerTournamentStats(player_id=by["old-boy"].id, tournament_id=lfl.id, played=0),
            PlayerTournamentStats(player_id=lfl_only.id, tournament_id=lfl.id, played=0),
            PlayerTournamentStats(
                player_id=by["aleksandr-korolev"].id, tournament_id=old_bl.id, played=9, goals=9
            ),
        ]
    )
    db.flush()
    recompute(db)


def test_players_by_league_sum_current_season_tournaments(client, db):
    _add_league_tournaments(db)
    bl = client.get("/players", params={"roster": "true", "league": "bl"}).json()
    assert [p["slug"] for p in bl] == ["egor-kucha", "aleksandr-korolev", "gone"]
    korolev = bl[1]["season"]
    assert (korolev["played"], korolev["goals"], korolev["assists"]) == (7, 3, 6)  # лига + кубок
    assert bl[2]["season"]["played"] == 1

    lfl = client.get("/players", params={"roster": "true", "league": "lfl"}).json()
    # old-boy в заявке ЛФЛ, но отчислен и не играл → не в составе
    assert [p["slug"] for p in lfl] == ["aleksandr-korolev", "lfl-only"]
    assert lfl[0]["season"]["goals"] == 4
    assert lfl[0]["season"]["yellow"] == 1
    assert lfl[1]["season"]["played"] == 0


def test_players_by_league_rejects_unknown_league(client):
    assert client.get("/players", params={"league": "xyz"}).status_code == 422
