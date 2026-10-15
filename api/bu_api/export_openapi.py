import json
import sys
from pathlib import Path

from bu_api.app import create_app


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
    schema = create_app(lambda: None).openapi()  # type: ignore[arg-type, return-value]
    target.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
