import pytest
from bu_core.text import normalize_name, player_slug, slugify, split_last_first


def test_normalize_name():
    assert normalize_name("  Фёдор   ИВАНОВ ") == "федор иванов"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Королев Александр", "korolev-aleksandr"),
        ("Bauman Junior", "bauman-junior"),
        ("Интер/Атон", "inter-aton"),
        ("Щукин Юрий", "shchukin-yuriy"),
        ("ФК ФН", "fk-fn"),
    ],
)
def test_slugify(value, expected):
    assert slugify(value) == expected


def test_split_last_first():
    assert split_last_first("Королев Александр") == ("Александр", "Королев")
    assert split_last_first("Пеле") == ("", "Пеле")


def test_player_slug():
    assert player_slug("Александр", "Королев") == "aleksandr-korolev"
