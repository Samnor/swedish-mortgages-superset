#!/usr/bin/env python3
"""Render the ECS task definition template from environment variables."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from string import Template


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: render_task_definition.py TEMPLATE OUTPUT", file=sys.stderr)
        return 2

    template_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    rendered = Template(template_path.read_text()).substitute(os.environ)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered)
    print(f"Rendered {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
