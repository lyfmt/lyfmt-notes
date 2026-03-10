#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

RUNTIME = Path("/home/node/.openclaw/workspace/.openclaw/runtime/rss-autopublish")
CURRENT = RUNTIME / "current-run.json"
LATEST = RUNTIME / "latest-run.json"


def load(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def summarize(run: dict | None) -> dict:
    if not isinstance(run, dict):
        return {"exists": False}
    return {
        "exists": True,
        "run_id": run.get("run_id"),
        "status": run.get("status"),
        "started_at": run.get("started_at"),
        "finished_at": run.get("finished_at"),
        "items_planned": run.get("items_planned"),
        "batch_summary": run.get("batch_summary"),
        "notes": run.get("notes") or [],
        "items": run.get("items") or [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Show the latest RSS autopublish run status.")
    parser.add_argument("--latest", action="store_true", help="Show latest-run.json instead of current-run.json")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    path = LATEST if args.latest else CURRENT
    payload = summarize(load(path))
    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
