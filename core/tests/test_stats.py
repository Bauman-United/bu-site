from datetime import UTC, datetime, timedelta

from bu_core.stats import Result, StatLine, form, leaders, outcome, records, totals

T0 = datetime(2026, 9, 1, tzinfo=UTC)


def r(i: int, us: int, them: int) -> Result:
    return Result(slug=f"m{i}", kickoff=T0 + timedelta(days=i), us=us, them=them)


def test_outcome():
    assert [outcome(2, 1), outcome(1, 1), outcome(0, 3)] == ["W", "D", "L"]


def test_form_last_five_oldest_first():
    results = [r(i, i % 3, 1) for i in range(7)]
    f = form(list(reversed(results)))
    assert [x["slug"] for x in f] == ["m2", "m3", "m4", "m5", "m6"]


def test_totals():
    t = totals([r(0, 2, 0), r(1, 1, 1), r(2, 0, 3)])
    assert t == {"played": 3, "won": 1, "drawn": 1, "lost": 1, "gf": 3, "ga": 4, "clean_sheets": 1}


def test_leaders_tiebreak_and_zero_filter():
    lines = [
        StatLine(1, "a", "Анна", played=5, goals=3, assists=0, yellow=0, red=0, mvp=0),
        StatLine(2, "b", "Борис", played=3, goals=3, assists=1, yellow=0, red=0, mvp=0),
        StatLine(3, "c", "Вера", played=4, goals=0, assists=0, yellow=0, red=0, mvp=0),
    ]
    top = leaders(lines, "goals")
    assert [x["slug"] for x in top] == ["b", "a"]
    assert top[0] == {"slug": "b", "name": "Борис", "value": 3, "played": 3}


def test_records():
    results = [r(0, 5, 1), r(1, 6, 2), r(2, 1, 1), r(3, 0, 1), r(4, 2, 0)]
    rec = records(
        results, goal_minutes=[("m1", 7), ("m0", 3)], appearances={"Анна": 10, "Борис": 12}
    )
    assert rec["biggest_win"] == {"slug": "m1", "us": 6, "them": 2}
    assert rec["unbeaten_streak"] == {"length": 3, "from": "m0", "to": "m2"}
    assert rec["fastest_goal"] == {"slug": "m0", "minute": 3}
    assert rec["most_appearances"] == {"name": "Борис", "value": 12}
    assert records([], [], {}) == {
        "biggest_win": None,
        "unbeaten_streak": None,
        "fastest_goal": None,
        "most_appearances": None,
    }
