#!/usr/bin/env python3
"""Render Superset datasource YAML from environment-specific settings."""

from __future__ import annotations

import os
from pathlib import Path
from string import Template


ROOT = Path(__file__).resolve().parents[1]
ASSETS_ROOT = Path(os.environ.get("CODEX_ASSETS_DIR", ROOT / "assets"))
TEMPLATE = ASSETS_ROOT / "datasources" / "swedish_mortgages.template.yaml"
OUTPUT = ASSETS_ROOT / "datasources" / "swedish_mortgages.yaml"


def load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def main() -> int:
    load_dotenv()
    values = {
        "SUPERSET_DATABASE_NAME": os.environ.get(
            "SUPERSET_DATABASE_NAME", "Athena Swedish Mortgages"
        ),
        "ATHENA_SCHEMA": os.environ.get("ATHENA_SCHEMA", "swedish_mortgages_dev_marts"),
    }
    rendered = Template(TEMPLATE.read_text()).substitute(values)
    OUTPUT.write_text(rendered)
    print(f"Rendered {OUTPUT} for schema {values['ATHENA_SCHEMA']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
