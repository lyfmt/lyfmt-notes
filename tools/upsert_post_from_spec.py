#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
import urllib.parse
import urllib.request
from copy import deepcopy
from pathlib import Path


DEFAULT_SUMMARY_HEADING = "文章核心"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upsert a static blog post entry into articles.json from a JSON spec, with optional media localization for GitHub Pages."
    )
    parser.add_argument("--spec", required=True, help="Path to a JSON file describing one post.")
    parser.add_argument("--articles", default="articles.json", help="Path to articles.json (default: articles.json)")
    parser.add_argument(
        "--assets-dir",
        default="assets/posts",
        help="Relative assets directory rooted at the site folder (default: assets/posts)",
    )
    parser.add_argument(
        "--localize-media",
        action="store_true",
        help="Download remote images in detail.blocks into assets/posts/<slug>/ and rewrite src to relative paths.",
    )
    parser.add_argument(
        "--append-new",
        action="store_true",
        help="Append new posts to the end instead of inserting at the beginning.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without writing files.")
    return parser.parse_args()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slugify(text: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "post"


def normalize_tags(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [part.strip() for part in value.split(",")]
    elif isinstance(value, list):
        items = [str(part).strip() for part in value]
    else:
        items = [str(value).strip()]
    seen = set()
    result = []
    for item in items:
        if not item:
            continue
        key = item.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def normalize_summary_content(content, fallback_excerpt: str) -> list[dict]:
    if isinstance(content, list):
        normalized = []
        for section in content:
            if isinstance(section, str):
                text = section.strip()
                if text:
                    normalized.append({"heading": DEFAULT_SUMMARY_HEADING, "paragraphs": [text]})
                continue
            if not isinstance(section, dict):
                continue
            heading = str(section.get("heading") or "").strip() or DEFAULT_SUMMARY_HEADING
            paragraphs = []
            for paragraph in section.get("paragraphs", []):
                text = str(paragraph).strip()
                if text:
                    paragraphs.append(text)
            if paragraphs:
                normalized.append({"heading": heading, "paragraphs": paragraphs})
        if normalized:
            return normalized
    fallback = (fallback_excerpt or "").strip()
    if fallback:
        return [{"heading": DEFAULT_SUMMARY_HEADING, "paragraphs": [fallback]}]
    return []


def normalize_detail(detail) -> dict:
    if not isinstance(detail, dict):
        return {"available": False}

    result = deepcopy(detail)
    blocks = result.get("blocks")
    if not isinstance(blocks, list):
        blocks = []
    result["blocks"] = [block for block in blocks if isinstance(block, dict) and block.get("type")]

    if "available" not in result:
        result["available"] = bool(result["blocks"])
    else:
        result["available"] = bool(result["available"])

    if not result["available"]:
        return {"available": False}

    result.setdefault("layout", "default")
    result.setdefault("sourceDescription", "以下为原文结构对应的中文整理版。")
    return result


def is_remote_url(value: str) -> bool:
    parsed = urllib.parse.urlparse(value or "")
    return parsed.scheme in {"http", "https"}


def guess_extension(url: str, content_type: str | None) -> str:
    path_ext = Path(urllib.parse.urlparse(url).path).suffix.lower()
    if path_ext:
        return path_ext
    if content_type:
        guessed = mimetypes.guess_extension(content_type.split(";", 1)[0].strip())
        if guessed:
            return guessed
    return ".bin"


def download_file(url: str, target: Path, dry_run: bool = False) -> None:
    if dry_run:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "OpenClaw RSS Summary Detail Importer/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read()
        target.write_bytes(payload)


def localize_detail_media(post: dict, site_root: Path, assets_dir: Path, dry_run: bool = False) -> list[str]:
    detail = post.get("detail") or {}
    if not detail.get("available"):
        return []

    slug = post["slug"]
    downloads = []
    image_index = 0

    for block in detail.get("blocks", []):
        if block.get("type") != "image":
            continue
        src = str(block.get("src") or "").strip()
        if not is_remote_url(src):
            continue

        image_index += 1
        request = urllib.request.Request(src, headers={"User-Agent": "OpenClaw RSS Summary Detail Importer/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            content_type = response.headers.get("Content-Type")
            payload = response.read()

        ext = guess_extension(src, content_type)
        filename = f"figure-{image_index:02d}{ext}"
        relative_asset_path = assets_dir / slug / filename
        target_path = site_root / relative_asset_path

        if not dry_run:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_bytes(payload)

        block["src"] = f"./{relative_asset_path.as_posix()}"
        downloads.append(relative_asset_path.as_posix())

    return downloads


def merge_post(existing: dict | None, spec: dict) -> dict:
    post = deepcopy(existing or {})

    slug = str(spec.get("slug") or post.get("slug") or slugify(spec.get("title") or "")).strip()
    if not slug:
        raise SystemExit("Post spec must include at least a title or slug.")
    post["slug"] = slug

    scalar_fields = ["title", "author", "publishedAt", "source", "url", "excerpt"]
    for field in scalar_fields:
        if field in spec:
            post[field] = str(spec.get(field) or "").strip()
        else:
            post.setdefault(field, "")

    if "tags" in spec:
        post["tags"] = normalize_tags(spec.get("tags"))
    else:
        post["tags"] = normalize_tags(post.get("tags"))

    if "content" in spec:
        post["content"] = normalize_summary_content(spec.get("content"), post.get("excerpt", ""))
    elif "content" not in post:
        post["content"] = normalize_summary_content([], post.get("excerpt", ""))

    if "detail" in spec:
        post["detail"] = normalize_detail(spec.get("detail"))
    else:
        post["detail"] = normalize_detail(post.get("detail"))

    return post


def upsert_post(articles_payload: dict, post: dict, append_new: bool = False) -> tuple[str, int]:
    posts = articles_payload.setdefault("posts", [])
    for idx, existing in enumerate(posts):
        if isinstance(existing, dict) and existing.get("slug") == post.get("slug"):
            posts[idx] = post
            return "updated", idx
    if append_new:
        posts.append(post)
        return "inserted", len(posts) - 1
    posts.insert(0, post)
    return "inserted", 0


def main() -> int:
    args = parse_args()
    spec_path = Path(args.spec).resolve()
    articles_path = Path(args.articles).resolve()
    site_root = articles_path.parent
    assets_dir = Path(args.assets_dir)

    spec = load_json(spec_path)
    if not isinstance(spec, dict):
        raise SystemExit("Spec JSON must be an object describing one post.")

    articles_payload = load_json(articles_path)
    posts = articles_payload.get("posts")
    if not isinstance(posts, list):
        raise SystemExit("articles.json must contain a top-level 'posts' array.")

    existing = None
    existing_slug = str(spec.get("slug") or "").strip()
    if existing_slug:
        existing = next((item for item in posts if isinstance(item, dict) and item.get("slug") == existing_slug), None)
    elif spec.get("title"):
        title = str(spec.get("title")).strip()
        existing = next((item for item in posts if isinstance(item, dict) and item.get("title") == title), None)

    post = merge_post(existing, spec)

    downloads = []
    if args.localize_media:
        downloads = localize_detail_media(post, site_root=site_root, assets_dir=assets_dir, dry_run=args.dry_run)

    action, index = upsert_post(articles_payload, post, append_new=args.append_new)

    if args.dry_run:
        print(f"[dry-run] {action} post '{post['slug']}' at index {index}")
    else:
        write_json(articles_path, articles_payload)
        print(f"{action} post '{post['slug']}' at index {index}")

    if downloads:
        print("localized media:")
        for item in downloads:
            print(f"- {item}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
