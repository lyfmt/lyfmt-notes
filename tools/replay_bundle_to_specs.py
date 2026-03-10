#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

WORKSPACE = Path("/home/node/.openclaw/workspace")
SITE_ROOT = WORKSPACE / "pi-blog-demo"
BUILD_SPEC = SITE_ROOT / "tools" / "build_post_spec_from_bundle.py"
BUILD_DETAIL = SITE_ROOT / "tools" / "build_detail_from_cache.py"
UPSERT = SITE_ROOT / "tools" / "upsert_post_from_spec.py"
VALIDATE = SITE_ROOT / "tools" / "validate_articles.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay a saved RSS bundle into specs/details/upserts for local testing.")
    parser.add_argument("--bundle", required=True, help="Path to saved bundle JSON")
    parser.add_argument("--ids", nargs="*", type=int, default=[], help="Optional article ids to replay")
    parser.add_argument("--skip-detail", action="store_true")
    parser.add_argument("--skip-upsert", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def run(cmd: list[str], *, cwd: Path, stdin_text: str | None = None) -> int:
    proc = subprocess.run(cmd, cwd=str(cwd), input=stdin_text, text=True, check=False)
    return proc.returncode


def main() -> int:
    args = parse_args()
    bundle_path = Path(args.bundle).resolve()
    if not bundle_path.exists():
        raise SystemExit(f"bundle not found: {bundle_path}")

    build_spec_cmd = ["python3", str(BUILD_SPEC), "--bundle", str(bundle_path), "--cache-metadata", "--cache-html"]
    for article_id in args.ids:
        build_spec_cmd.extend(["--id", str(article_id)])
    if args.dry_run:
        build_spec_cmd.append("--dry-run")
    if run(build_spec_cmd, cwd=SITE_ROOT) != 0:
        return 1

    if args.skip_detail:
        return 0

    spec_dir = SITE_ROOT / "tools" / "generated-specs"
    spec_paths = sorted(spec_dir.glob("*.json"))
    if args.ids:
        allowed = set(args.ids)
        filtered = []
        for spec_path in spec_paths:
            text = spec_path.read_text(encoding="utf-8")
            if any(f'"articleId": {article_id}' in text for article_id in allowed):
                filtered.append(spec_path)
        spec_paths = filtered

    for spec_path in spec_paths:
        detail_cmd = ["python3", str(BUILD_DETAIL), "--spec", str(spec_path), "--write-spec"]
        if args.dry_run:
            detail_cmd.append("--dry-run")
        if run(detail_cmd, cwd=SITE_ROOT) != 0:
            return 1
        if not args.skip_upsert:
            upsert_cmd = ["python3", str(UPSERT), "--spec", str(spec_path), "--articles", str(SITE_ROOT / 'articles.json')]
            if args.dry_run:
                upsert_cmd.append("--dry-run")
            if run(upsert_cmd, cwd=SITE_ROOT) != 0:
                return 1

    if not args.skip_upsert:
        validate_cmd = ["python3", str(VALIDATE), "--articles", str(SITE_ROOT / 'articles.json'), "--pretty"]
        return run(validate_cmd, cwd=SITE_ROOT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
