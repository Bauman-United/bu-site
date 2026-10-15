import pytest
from bu_core.matching import AmbiguousMatchError, PlayerIndex, PlayerName


def make_index():
    return PlayerIndex(
        [
            PlayerName(1, "Александр", "Королев"),
            PlayerName(2, "Кирилл", "Колочков", aliases=("Киря",)),
        ]
    )


def test_find_by_both_orders_and_yo():
    idx = make_index()
    assert idx.find("Королев Александр") == 1
    assert idx.find("александр  королёв") == 1


def test_find_by_alias_and_missing():
    idx = make_index()
    assert idx.find("Киря") == 2
    assert idx.find("Неизвестный Игрок") is None


def test_ambiguous():
    idx = make_index()
    idx.add(PlayerName(3, "Александр", "Королев"))
    with pytest.raises(AmbiguousMatchError) as err:
        idx.find("Королев Александр")
    assert err.value.ids == [1, 3]
