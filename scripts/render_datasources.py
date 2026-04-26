#!/usr/bin/env python3
"""Render Superset datasource YAML from environment-specific settings."""

from __future__ import annotations

import os
from pathlib import Path
from string import Template
from urllib.parse import quote_plus


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
    athena_region = os.environ.get("ATHENA_REGION", "eu-north-1")
    athena_schema = os.environ.get("ATHENA_SCHEMA", "swedish_mortgages_dev_marts")
    athena_database = os.environ.get("ATHENA_DATABASE", athena_schema)
    if athena_database.lower() == "awsdatacatalog":
        athena_database = athena_schema
    athena_work_group = os.environ.get("ATHENA_WORK_GROUP", "primary")
    athena_staging_dir = os.environ.get("ATHENA_S3_STAGING_DIR", "")
    athena_uri = os.environ.get("ATHENA_SQLALCHEMY_URI") or (
        "awsathena+rest://@"
        f"athena.{athena_region}.amazonaws.com/{athena_database}"
        f"?work_group={quote_plus(athena_work_group)}"
        f"&s3_staging_dir={quote_plus(athena_staging_dir)}"
    )
    values = {
        "SUPERSET_DATABASE_NAME": os.environ.get(
            "SUPERSET_DATABASE_NAME", "Athena Swedish Mortgages"
        ),
        "ATHENA_SCHEMA": athena_schema,
        "ATHENA_SQLALCHEMY_URI": athena_uri,
    }
    rendered = Template(TEMPLATE.read_text()).substitute(values)
    OUTPUT.write_text(rendered)
    print(f"Rendered {OUTPUT} for schema {values['ATHENA_SCHEMA']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
