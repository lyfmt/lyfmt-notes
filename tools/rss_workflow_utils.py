#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import tempfile
from copy import deepcopy
from pathlib import Path
from typing import Any

CHALLENGE_TITLE_PATTERNS = [
    re.compile(r"^just a moment", re.IGNORECASE),
    re.compile(r"^attention required", re.IGNORECASE),
    re.compile(r"^access denied", re.IGNORECASE),
    re.compile(r"^please wait", re.IGNORECASE),
    re.compile(r"^checking your browser", re.IGNORECASE),
    re.compile(r"^verify you are human", re.IGNORECASE),
    re.compile(r"^security check", re.IGNORECASE),
]

CHALLENGE_TEXT_MARKERS = [
    "cloudflare",
    "cf-browser-verification",
    "attention required!",
    "just a moment",
    "checking if the site connection is secure",
    "enable javascript and cookies to continue",
    "verify you are human",
    "ddos protection by cloudflare",
    "please stand by, while we are checking your browser",
    "security check to access",
    "captcha",
]

GENERIC_BAD_TITLES = {
    "home",
    "untitled",
    "error",
    "403 forbidden",
    "502 bad gateway",
    "503 service unavailable",
}

TEXTUAL_BLOCK_TYPES = {"heading", "paragraph", "footnote", "list"}


def normalize_space(value: str | None) -> str:
    text = str(value or "")
    return re.sub(r"\s+", " ", text).strip()


def slugify(text: str) -> str:
    value = normalize_space(text).lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "post"


def is_suspicious_title(title: str | None) -> bool:
    text = normalize_space(title).casefold()
    if not text:
        return True
    if text in GENERIC_BAD_TITLES:
        return True
    if any(pattern.search(text) for pattern in CHALLENGE_TITLE_PATTERNS):
        return True
    if len(text) <= 3:
        return True
    return False


def classify_web_content(title: str | None = None, text: str | None = None) -> str:
    normalized_title = normalize_space(title).casefold()
    normalized_text = normalize_space(text).casefold()
    if is_suspicious_title(normalized_title):
        return "challenge"
    if any(marker in normalized_text for marker in CHALLENGE_TEXT_MARKERS):
        return "challenge"
    if normalized_text and len(normalized_text) < 120:
        return "thin"
    return "normal"


def choose_preferred_title(item_title: str | None, probe_title: str | None) -> str:
    preferred_item = normalize_space(item_title)
    preferred_probe = normalize_space(probe_title)
    if preferred_probe and not is_suspicious_title(preferred_probe):
        return preferred_probe
    return preferred_item or preferred_probe or "Untitled"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(path.parent), encoding="utf-8") as tmp:
        json.dump(payload, tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def load_articles_payload(path: Path) -> dict:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"articles payload must be an object: {path}")
    posts = payload.get("posts")
    if not isinstance(posts, list):
        raise ValueError(f"articles payload missing posts array: {path}")
    return payload


def find_existing_post(posts: list[dict], slug: str | None = None, url: str | None = None, title: str | None = None) -> dict | None:
    normalized_slug = normalize_space(slug)
    normalized_url = normalize_space(url)
    normalized_title = normalize_space(title)

    if normalized_slug:
        for post in posts:
            if isinstance(post, dict) and normalize_space(post.get("slug")) == normalized_slug:
                return post
    if normalized_url:
        for post in posts:
            if isinstance(post, dict) and normalize_space(post.get("url")) == normalized_url:
                return post
    if normalized_title:
        for post in posts:
            if isinstance(post, dict) and normalize_space(post.get("title")) == normalized_title:
                return post
    return None


def has_cjk(text: str | None) -> bool:
    return bool(re.search(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]", str(text or "")))


def block_has_cjk(block: dict) -> bool:
    block_type = block.get("type")
    if block_type == "heading":
        return has_cjk(block.get("text"))
    if block_type in {"paragraph", "footnote"}:
        return has_cjk(block.get("html"))
    if block_type == "list":
        return any(has_cjk(item) for item in (block.get("items") or []))
    if block_type == "image":
        return has_cjk(block.get("alt")) or has_cjk(block.get("caption"))
    if block_type == "embed":
        return has_cjk(block.get("title"))
    return False


def block_text_nonempty(block: dict) -> bool:
    block_type = block.get("type")
    if block_type == "heading":
        return bool(normalize_space(block.get("text")))
    if block_type in {"paragraph", "footnote"}:
        return bool(normalize_space(block.get("html")))
    if block_type == "list":
        return any(normalize_space(item) for item in (block.get("items") or []))
    return False


def detail_progress(detail: dict | None) -> dict[str, int]:
    payload = detail if isinstance(detail, dict) else {}
    blocks = payload.get("blocks") if isinstance(payload.get("blocks"), list) else []
    textual_blocks = [block for block in blocks if isinstance(block, dict) and block.get("type") in TEXTUAL_BLOCK_TYPES and block_text_nonempty(block)]
    textual_cjk = [block for block in textual_blocks if block_has_cjk(block)]
    return {
        "block_count": len(blocks),
        "textual_total": len(textual_blocks),
        "textual_cjk": len(textual_cjk),
    }


def is_detail_publishable(detail: dict | None) -> bool:
    progress = detail_progress(detail)
    if progress["block_count"] <= 0:
        return False
    if progress["textual_total"] <= 0:
        return bool(isinstance(detail, dict) and detail.get("available"))
    return progress["textual_cjk"] >= progress["textual_total"]


def pick_richer_detail(existing: dict | None, incoming: dict | None) -> dict:
    existing_detail = deepcopy(existing) if isinstance(existing, dict) else {"available": False}
    incoming_detail = deepcopy(incoming) if isinstance(incoming, dict) else {"available": False}

    existing_progress = detail_progress(existing_detail)
    incoming_progress = detail_progress(incoming_detail)

    if is_detail_publishable(incoming_detail):
        result = incoming_detail
        result["available"] = True
        return result
    if is_detail_publishable(existing_detail) and not is_detail_publishable(incoming_detail):
        result = existing_detail
        result["available"] = True
        return result

    if incoming_progress["block_count"] > existing_progress["block_count"]:
        result = incoming_detail
    elif incoming_progress["textual_cjk"] > existing_progress["textual_cjk"]:
        result = incoming_detail
    elif existing_progress["block_count"] > 0:
        result = existing_detail
    else:
        result = incoming_detail

    result = deepcopy(result)
    result["available"] = bool(is_detail_publishable(result))
    return result


def build_blocked_detail(url: str, source_name: str, message: str) -> dict:
    return {
        "available": False,
        "layout": "draft",
        "translatedFrom": normalize_space(url),
        "sourceName": normalize_space(source_name),
        "sourceDescription": message,
        "blocks": [
            {
                "type": "paragraph",
                "html": message,
            }
        ],
    }
