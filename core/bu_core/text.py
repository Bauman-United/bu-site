import re

_TRANSLIT = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "kh",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "shch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)


def normalize_name(value: str) -> str:
    return " ".join(value.lower().replace("ё", "е").split())


def slugify(value: str) -> str:
    latin = value.lower().translate(_TRANSLIT)
    return re.sub(r"[^a-z0-9]+", "-", latin).strip("-")


def split_last_first(full_name: str) -> tuple[str, str]:
    """Имя в источниках идёт как «Фамилия Имя». Возвращает (имя, фамилия)."""
    parts = full_name.split()
    if not parts:
        raise ValueError("empty name")
    return " ".join(parts[1:]), parts[0]


def player_slug(first_name: str, last_name: str) -> str:
    return slugify(f"{first_name} {last_name}")
