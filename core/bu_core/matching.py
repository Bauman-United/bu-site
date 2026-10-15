from collections.abc import Iterable
from dataclasses import dataclass

from bu_core.text import normalize_name


@dataclass(frozen=True)
class PlayerName:
    id: int
    first_name: str
    last_name: str
    aliases: tuple[str, ...] = ()


class AmbiguousMatchError(Exception):
    def __init__(self, name: str, ids: list[int]):
        super().__init__(f"ambiguous player name {name!r}: candidates {ids}")
        self.name = name
        self.ids = ids


class PlayerIndex:
    """Поиск игрока по ФИО в любом порядке слов и по алиасам."""

    def __init__(self, players: Iterable[PlayerName] = ()):
        self._by_key: dict[str, set[int]] = {}
        for p in players:
            self.add(p)

    def add(self, p: PlayerName) -> None:
        keys = {
            normalize_name(f"{p.last_name} {p.first_name}"),
            normalize_name(f"{p.first_name} {p.last_name}"),
            *(normalize_name(a) for a in p.aliases),
        }
        for key in keys:
            if key:
                self._by_key.setdefault(key, set()).add(p.id)

    def find(self, full_name: str) -> int | None:
        ids = sorted(self._by_key.get(normalize_name(full_name), set()))
        if not ids:
            return None
        if len(ids) > 1:
            raise AmbiguousMatchError(full_name, ids)
        return ids[0]
