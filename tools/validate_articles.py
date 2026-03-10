#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from rss_workflow_utils import is_suspicious_title, load_articles_payload, normalize_space


REQUIRED_POST_FIELDS = ["slug", "title", "publishedAt", "source", "url", "excerpt"]


def validate_articles(path: Path) -> dict:
    payload = load_articles_payload(path)
    posts = payload.get("posts") or []
    errors: list[str] = []
    warnings: list[str] = []
    seen_slugs: dict[str, int] = {}
    seen_urls: dict[str, int] = {}

    for index, post in enumerate(posts):
        if not isinstance(post, dict):
            errors.append(f"posts[{index}] is not an object")
            continue

        label = f"posts[{index}]"
        for field in REQUIRED_POST_FIELDS:
            if not normalize_space(post.get(field)):
                errors.append(f"{label} missing required field: {field}")

        slug = normalize_space(post.get("slug"))
        title = normalize_space(post.get("title"))
        url = normalize_space(post.get("url"))
        if slug:
            if slug in seen_slugs:
                errors.append(f"duplicate slug '{slug}' at posts[{seen_slugs[slug]}] and {label}")
            else:
                seen_slugs[slug] = index
        if url:
            if url in seen_urls:
                warnings.append(f"duplicate url '{url}' at posts[{seen_urls[url]}] and {label}")
            else:
                seen_urls[url] = index

        if is_suspicious_title(title):
            errors.append(f"{label} has suspicious title: {title!r}")
        if slug and title and slug == "just-a-moment":
            errors.append(f"{label} uses polluted slug 'just-a-moment'")

        detail = post.get("detail")
        if detail is not None and not isinstance(detail, dict):
            errors.append(f"{label}.detail is not an object")
        elif isinstance(detail, dict):
            blocks = detail.get("blocks")
            if blocks is not None and not isinstance(blocks, list):
                errors.append(f"{label}.detail.blocks is not a list")
            if isinstance(blocks, list):
                for block_index, block in enumerate(blocks):
                    if not isinstance(block, dict):
                        errors.append(f"{label}.detail.blocks[{block_index}] is not an object")
                        continue
                    if not normalize_space(block.get("type")):
                        errors.append(f"{label}.detail.blocks[{block_index}] missing type")

    return {
        "ok": not errors,
        "path": str(path),
        "post_count": len(posts),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate pi-blog-demo articles.json for publish safety.")
    parser.add_argument("--articles", default="articles.json", help="Path to articles.json")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    result = validate_articles(Path(args.articles).resolve())
    if args.pretty:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
