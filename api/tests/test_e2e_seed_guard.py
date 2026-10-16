import pytest
from bu_api.e2e_seed import ensure_e2e_database


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://localhost/bu_e2e",
        "postgresql+psycopg://localhost/bu_e2e_empty",
        "postgresql+psycopg://user:pw@db:5432/site_e2e",
    ],
)
def test_allows_e2e_databases(url):
    ensure_e2e_database(url)


@pytest.mark.parametrize(
    "url",
    [
        "postgresql+psycopg://localhost/bu",
        "postgresql+psycopg://localhost/bu_e2e_prod",
        "postgresql+psycopg://localhost/e2e",
        "postgresql+psycopg://localhost/",
        "sqlite://",
    ],
)
def test_refuses_other_databases(url, capsys):
    with pytest.raises(SystemExit) as exc:
        ensure_e2e_database(url)
    assert exc.value.code != 0
    assert "_e2e" in capsys.readouterr().err


def test_main_refuses_before_touching_the_database(monkeypatch):
    import bu_api.e2e_seed as seed_mod

    def boom(*_a, **_k):
        raise AssertionError("create_engine must not be called for a non-e2e database")

    monkeypatch.setattr(seed_mod, "create_engine", boom)
    monkeypatch.setattr("sys.argv", ["e2e_seed", "postgresql+psycopg://localhost/bu"])
    with pytest.raises(SystemExit):
        seed_mod.main()
