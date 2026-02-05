#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: parse_metadata.py <metadata.json>", file=sys.stderr)
        return 1

    path = Path(sys.argv[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Metadata file not found: {path}", file=sys.stderr)
        return 1
    except json.JSONDecodeError:
        print(f"Failed to parse metadata JSON. Check {path} format.", file=sys.stderr)
        return 1

    proton_version = data.get("proton_version")
    if not proton_version:
        print("Metadata JSON missing proton_version. Re-run the build step.", file=sys.stderr)
        return 1

    print(proton_version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
