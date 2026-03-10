#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path

from rss_workflow_utils import build_blocked_detail, classify_web_content, load_json as load_json_file, normalize_space


WORKSPACE = Path("/home/node/.openclaw/workspace")
SITE_ROOT = WORKSPACE / "pi-blog-demo"
DEFAULT_SOURCE_CACHE = SITE_ROOT / "source-cache"
DEFAULT_OUTPUT_DIR = SITE_ROOT / "tools" / "generated-details"
USER_AGENT = "OpenClaw Detail Builder/1.0"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build detail.blocks[] draft content from source-cache Markdown/HTML for pi-blog-demo posts."
    )
    parser.add_argument("--spec", required=True, help="Path to a generated post spec JSON.")
    parser.add_argument("--source", help="Path to source markdown/html. If omitted, auto-detect from source-cache by slug.")
    parser.add_argument("--source-cache-dir", default=str(DEFAULT_SOURCE_CACHE), help="Directory containing cached source files.")
    parser.add_argument("--output", help="Path to write the generated detail payload JSON.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for generated detail JSON drafts.")
    parser.add_argument("--write-spec", action="store_true", help="Write the generated detail payload back into the spec JSON.")
    parser.add_argument("--enable-detail", action="store_true", help="Set detail.available=true when writing into the spec.")
    parser.add_argument("--layout", default="draft", help="detail.layout value (default: draft)")
    parser.add_argument("--translated-from", help="Override detail.translatedFrom; defaults to spec.url or source path.")
    parser.add_argument("--source-name", help="Override detail.sourceName; defaults to spec.source.")
    parser.add_argument(
        "--source-description",
        default="以下为根据原文结构自动生成的详情草稿，已保留段落层次、图片与媒体；默认尚未完成中文翻译润色。",
        help="detail.sourceDescription value.",
    )
    parser.add_argument("--cache-html", action="store_true", help="If the source file is missing, fetch spec.url and cache it as source-cache/<slug>.html.")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without writing files.")
    return parser.parse_args()


def load_json(path: Path):
    return load_json_file(path)


def write_json(path: Path, payload, dry_run: bool = False) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def slugify(text: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "post"


def resolve_url(url: str, base_url: str | None) -> str:
    url = normalize_space(url)
    if not url:
        return ""
    if not base_url:
        return url
    return urllib.parse.urljoin(base_url, url)


ATTR_RE = re.compile(r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(".*?"|\'.*?\'|[^\s"\'>]+)')


def parse_tag_attrs(fragment: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, value in ATTR_RE.findall(fragment):
        if value[:1] in {'"', "'"}:
            value = value[1:-1]
        attrs[name.lower()] = unescape(value)
    return attrs


def sanitize_href(url: str, base_url: str | None) -> str:
    resolved = resolve_url(url, base_url)
    return escape(resolved, quote=True)


def inline_markdown_to_html(text: str, base_url: str | None) -> str:
    tokens: dict[str, str] = {}
    counter = 0

    def token(html_value: str) -> str:
        nonlocal counter
        counter += 1
        key = f"@@TOKEN_{counter}@@"
        tokens[key] = html_value
        return key

    def replace_code(match: re.Match[str]) -> str:
        return token(f"<code>{escape(match.group(1))}</code>")

    def replace_link(match: re.Match[str]) -> str:
        label = inline_markdown_to_html(match.group(1), base_url)
        href = sanitize_href(match.group(2), base_url)
        return token(f'<a href="{href}" target="_blank" rel="noreferrer noopener">{label}</a>')

    def replace_footnote_ref(match: re.Match[str]) -> str:
        return token(f"<sup>[{escape(match.group(1))}]</sup>")

    value = text
    value = re.sub(r"`([^`]+)`", replace_code, value)
    value = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", replace_link, value)
    value = re.sub(r"\[\^([^\]]+)\]", replace_footnote_ref, value)
    value = escape(value)
    value = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"(?<!\*)\*(.+?)\*(?!\*)", r"<em>\1</em>", value)

    for key, html_value in tokens.items():
        value = value.replace(escape(key), html_value)
        value = value.replace(key, html_value)

    return value


def collect_html_block(lines: list[str], start: int) -> tuple[str, int]:
    buffer = [lines[start].strip()]
    line = lines[start].strip().lower()
    tag = "iframe" if line.startswith("<iframe") else "img"
    index = start

    if tag == "img" and ">" in buffer[0]:
        return buffer[0], index + 1

    while index + 1 < len(lines):
        index += 1
        buffer.append(lines[index].strip())
        joined = " ".join(buffer).lower()
        if tag == "iframe" and "</iframe>" in joined:
            break
        if tag == "img" and ">" in joined:
            break
    return " ".join(buffer), index + 1


def parse_image_fragment(fragment: str, base_url: str | None) -> dict | None:
    match = re.search(r"<img\b([^>]*?)>", fragment, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    attrs = parse_tag_attrs(match.group(1))
    src = resolve_url(attrs.get("src", ""), base_url)
    if not src:
        return None
    return {
        "type": "image",
        "src": src,
        "alt": attrs.get("alt", ""),
        "caption": attrs.get("title", "") or attrs.get("alt", ""),
    }


def parse_iframe_fragment(fragment: str, base_url: str | None) -> dict | None:
    match = re.search(r"<iframe\b([^>]*?)>", fragment, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    attrs = parse_tag_attrs(match.group(1))
    src = resolve_url(attrs.get("src", ""), base_url)
    if not src:
        return None
    provider = "youtube" if "youtube.com" in src or "youtu.be" in src else "embed"
    return {
        "type": "embed",
        "provider": provider,
        "src": src,
        "title": attrs.get("title", "Embedded media") or "Embedded media",
    }


def parse_markdown_blocks(text: str, base_url: str | None, title: str | None = None) -> list[dict]:
    blocks: list[dict] = []
    lines = text.splitlines()
    i = 0
    first_heading_skipped = False

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip("\n")
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped.startswith("<img") or stripped.startswith("<iframe"):
            fragment, next_i = collect_html_block(lines, i)
            block = parse_image_fragment(fragment, base_url) if stripped.startswith("<img") else parse_iframe_fragment(fragment, base_url)
            if block:
                blocks.append(block)
            i = next_i
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            text_value = normalize_space(heading_match.group(2))
            if level == 1 and not first_heading_skipped and title and text_value.casefold() == title.casefold():
                first_heading_skipped = True
                i += 1
                continue
            if level == 1 and not first_heading_skipped:
                first_heading_skipped = True
                i += 1
                continue
            blocks.append({"type": "heading", "level": min(max(level, 2), 3), "text": text_value})
            i += 1
            continue

        footnote_match = re.match(r"^\[\^([^\]]+)\]:\s*(.*)$", stripped)
        if footnote_match:
            label = footnote_match.group(1)
            parts = [footnote_match.group(2).strip()]
            j = i + 1
            while j < len(lines):
                continuation = lines[j]
                if continuation.startswith("  ") or continuation.startswith("\t"):
                    parts.append(continuation.strip())
                    j += 1
                    continue
                break
            html_value = inline_markdown_to_html(" ".join(part for part in parts if part), base_url)
            blocks.append({"type": "footnote", "html": f"<strong>注 {escape(label)}</strong>：{html_value}"})
            i = j
            continue

        list_match = re.match(r"^(?:[*-]|\d+\.)\s+(.*)$", stripped)
        if list_match:
            items: list[str] = []
            j = i
            current_item = ""
            while j < len(lines):
                candidate = lines[j].rstrip("\n")
                candidate_stripped = candidate.strip()
                bullet_match = re.match(r"^(?:[*-]|\d+\.)\s+(.*)$", candidate_stripped)
                if bullet_match:
                    if current_item:
                        items.append(inline_markdown_to_html(current_item.strip(), base_url))
                    current_item = bullet_match.group(1).strip()
                    j += 1
                    continue
                if candidate.startswith("  ") or candidate.startswith("\t"):
                    current_item += " " + candidate.strip()
                    j += 1
                    continue
                break
            if current_item:
                items.append(inline_markdown_to_html(current_item.strip(), base_url))
            if items:
                blocks.append({"type": "list", "items": items})
            i = j
            continue

        image_md_match = re.match(r"^!\[([^\]]*)\]\(([^)\s]+)(?:\s+\"([^\"]+)\")?\)$", stripped)
        if image_md_match:
            blocks.append({
                "type": "image",
                "src": resolve_url(image_md_match.group(2), base_url),
                "alt": image_md_match.group(1) or "",
                "caption": image_md_match.group(3) or image_md_match.group(1) or "",
            })
            i += 1
            continue

        paragraph_lines = [stripped]
        j = i + 1
        while j < len(lines):
            candidate = lines[j]
            candidate_stripped = candidate.strip()
            if not candidate_stripped:
                break
            if (
                candidate_stripped.startswith("<img")
                or candidate_stripped.startswith("<iframe")
                or re.match(r"^(#{1,6})\s+", candidate_stripped)
                or re.match(r"^\[\^([^\]]+)\]:", candidate_stripped)
                or re.match(r"^(?:[*-]|\d+\.)\s+", candidate_stripped)
                or re.match(r"^!\[([^\]]*)\]\(([^)\s]+)", candidate_stripped)
            ):
                break
            paragraph_lines.append(candidate_stripped)
            j += 1

        paragraph = normalize_space(" ".join(paragraph_lines))
        if paragraph:
            blocks.append({"type": "paragraph", "html": inline_markdown_to_html(paragraph, base_url)})
        i = j if j > i else i + 1

    return blocks


INLINE_ALLOWED = {"a", "code", "em", "strong", "b", "i", "sup", "sub", "span"}
IGNORED_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "form", "button"}
HTML_CONTAINER_PATTERNS = [
    r'<(?P<tag>div|section|article|main)\b[^>]*\bid=["\']tns-post-body-content["\'][^>]*>',
    r'<(?P<tag>div|section|article|main)\b[^>]*\bid=["\']tns-post-body["\'][^>]*>',
    r'<(?P<tag>div|section|article|main)\b[^>]*\b(?:id|class)=["\'][^"\']*entry-content[^"\']*["\'][^>]*>',
    r'<(?P<tag>div|section|article|main)\b[^>]*\b(?:id|class)=["\'][^"\']*post-content[^"\']*["\'][^>]*>',
    r'<(?P<tag>div|section|article|main)\b[^>]*\b(?:id|class)=["\'][^"\']*article-content[^"\']*["\'][^>]*>',
    r'<(?P<tag>div|section|article|main)\b[^>]*\b(?:id|class)=["\'][^"\']*article-body[^"\']*["\'][^>]*>',
    r'<(?P<tag>div|section|article|main)\b[^>]*\b(?:id|class)=["\'][^"\']*story-body[^"\']*["\'][^>]*>',
    r'<(?P<tag>div|section|article|main)\b[^>]*\bitemprop=["\']articleBody["\'][^>]*>',
]
HTML_BOILERPLATE_PHRASES = [
    "check your inbox",
    "follow tns",
    "featured and trending stories",
    "while you wait for your first tns newsletter",
    "sponsored this post",
    "subscribe to",
    "sign up for",
    "follow us on",
]


def strip_ignored_html(text: str) -> str:
    value = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    for tag in ("script", "style", "noscript", "svg"):
        value = re.sub(fr"<{tag}\b.*?</{tag}>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    return value


def extract_balanced_element(text: str, start_index: int, tag_name: str) -> str:
    tag = tag_name.lower()
    pattern = re.compile(fr"<(/?){tag}\b[^>]*>", re.IGNORECASE)
    depth = 0
    start = None
    for match in pattern.finditer(text, start_index):
        closing = match.group(1) == "/"
        raw = match.group(0)
        self_closing = raw.rstrip().endswith("/>")
        if not closing:
            if start is None:
                start = match.start()
            depth += 1
            if self_closing:
                depth -= 1
                if depth == 0 and start is not None:
                    return text[start:match.end()]
        else:
            depth -= 1
            if depth == 0 and start is not None:
                return text[start:match.end()]
    if start is None:
        return ""
    return text[start:start + 80000]


def score_html_fragment(fragment: str) -> int:
    lowered = fragment.lower()
    paragraphs = len(re.findall(r"<p\b", fragment, re.IGNORECASE))
    headings = len(re.findall(r"<h[1-6]\b", fragment, re.IGNORECASE))
    list_items = len(re.findall(r"<li\b", fragment, re.IGNORECASE))
    images = len(re.findall(r"<img\b", fragment, re.IGNORECASE))
    embeds = len(re.findall(r"<iframe\b", fragment, re.IGNORECASE))
    text_len = len(re.sub(r"<[^>]+>", " ", fragment))
    penalties = sum(lowered.count(phrase) * 12 for phrase in HTML_BOILERPLATE_PHRASES)
    penalties += lowered.count("share-media-icon") * 5
    penalties += lowered.count("newsletter") * 8
    return paragraphs * 12 + headings * 10 + list_items * 5 + images * 4 + embeds * 4 + min(text_len // 300, 60) - penalties


def find_best_html_fragment(text: str, title: str | None = None) -> str:
    cleaned = strip_ignored_html(text)
    candidates: list[str] = []

    for pattern in HTML_CONTAINER_PATTERNS:
        match = re.search(pattern, cleaned, re.IGNORECASE)
        if not match:
            continue
        tag_name = match.group("tag")
        fragment = extract_balanced_element(cleaned, match.start(), tag_name)
        if fragment:
            candidates.append(fragment)

    if title:
        heading_match = re.search(
            rf"<h1\b[^>]*>.*?{re.escape(title)}.*?</h1>",
            cleaned,
            re.IGNORECASE | re.DOTALL,
        )
        if heading_match:
            start = heading_match.start()
            end_markers = [
                re.search(r"class=[\"']share-media-icon", cleaned[start:], re.IGNORECASE),
                re.search(r"id=[\"']comments", cleaned[start:], re.IGNORECASE),
                re.search(r"class=[\"'][^\"']*related[^\"']*[\"']", cleaned[start:], re.IGNORECASE),
            ]
            relative_positions = [m.start() for m in end_markers if m]
            if relative_positions:
                end = start + min(relative_positions)
            else:
                end = min(len(cleaned), start + 90000)
            candidates.append(cleaned[start:end])

    if not candidates:
        return cleaned

    candidates = sorted(candidates, key=score_html_fragment, reverse=True)
    return candidates[0]


def strip_tags(value: str) -> str:
    return normalize_space(re.sub(r"<[^>]+>", " ", value or ""))


def prune_boilerplate_blocks(blocks: list[dict], title: str | None = None) -> list[dict]:
    filtered: list[dict] = []
    normalized_title = normalize_space(title).casefold() if title else ""

    for block in blocks:
        block_type = block.get("type")
        text_parts: list[str] = []
        if block_type == "heading":
            text_parts.append(str(block.get("text") or ""))
        elif block_type in {"paragraph", "footnote"}:
            text_parts.append(strip_tags(str(block.get("html") or "")))
        elif block_type == "list":
            text_parts.extend(strip_tags(str(item)) for item in block.get("items") or [])
        elif block_type == "image":
            text_parts.append(normalize_space(str(block.get("alt") or "")))
            text_parts.append(normalize_space(str(block.get("caption") or "")))
        elif block_type == "embed":
            text_parts.append(normalize_space(str(block.get("title") or "")))

        normalized = normalize_space(" ".join(part for part in text_parts if part)).casefold()
        if normalized_title and normalized == normalized_title:
            continue
        if normalized and any(phrase in normalized for phrase in HTML_BOILERPLATE_PHRASES):
            continue
        filtered.append(block)

    return filtered


class DetailHTMLParser(HTMLParser):
    def __init__(self, base_url: str | None, title: str | None, preferred_root: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title = normalize_space(title)
        self.preferred_root = preferred_root
        self.blocks: list[dict] = []
        self.ignore_depth = 0
        self.root_depth = 0
        self.body_depth = 0
        self.current_block: dict | None = None
        self.current_block_fragments: list[str] = []
        self.list_items: list[str] | None = None
        self.current_li_fragments: list[str] | None = None
        self.current_figcaption: list[str] | None = None
        self.figure_image_index: int | None = None
        self.figure_depth = 0
        self.seen_title_heading = False

    def is_capturing(self) -> bool:
        if self.ignore_depth > 0:
            return False
        if self.preferred_root == "document":
            return True
        if self.preferred_root == "body":
            return self.body_depth > 0
        return self.root_depth > 0

    def push_inline_start(self, tag: str, attrs: dict[str, str]) -> None:
        if tag == "a":
            href = sanitize_href(attrs.get("href", ""), self.base_url)
            self.append_fragment(f'<a href="{href}" target="_blank" rel="noreferrer noopener">')
            return
        if tag == "span":
            self.append_fragment("<span>")
            return
        self.append_fragment(f"<{tag}>")

    def push_inline_end(self, tag: str) -> None:
        if tag in {"a", "code", "em", "strong", "b", "i", "sup", "sub", "span"}:
            self.append_fragment(f"</{tag}>")

    def append_fragment(self, text: str) -> None:
        if self.current_figcaption is not None:
            self.current_figcaption.append(text)
        elif self.current_li_fragments is not None:
            self.current_li_fragments.append(text)
        elif self.current_block_fragments is not None:
            self.current_block_fragments.append(text)

    def flush_current_block(self) -> None:
        if not self.current_block:
            self.current_block_fragments = []
            return
        html_value = normalize_space("".join(self.current_block_fragments)).strip()
        block_type = self.current_block.get("type")
        if block_type == "paragraph" and html_value:
            self.blocks.append({"type": "paragraph", "html": html_value})
        elif block_type == "heading" and html_value:
            text_value = re.sub(r"<[^>]+>", "", html_value).strip()
            if text_value:
                if not (self.current_block.get("level") == 1 and (not self.seen_title_heading) and self.title and text_value.casefold() == self.title.casefold()):
                    self.blocks.append({"type": "heading", "level": min(max(int(self.current_block.get("level", 2)), 2), 3), "text": text_value})
                self.seen_title_heading = True
        self.current_block = None
        self.current_block_fragments = []

    def handle_starttag(self, tag: str, attrs_list):
        tag = tag.lower()
        attrs = {str(key).lower(): str(value) for key, value in attrs_list if key}

        if tag in IGNORED_TAGS:
            self.ignore_depth += 1
            return

        if tag == "body":
            self.body_depth += 1
        if tag == self.preferred_root:
            self.root_depth += 1

        if not self.is_capturing():
            return

        if tag == "figure":
            self.figure_depth += 1
            self.figure_image_index = None
            return
        if tag == "figcaption":
            self.current_figcaption = []
            return
        if tag == "p":
            self.flush_current_block()
            self.current_block = {"type": "paragraph"}
            self.current_block_fragments = []
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.flush_current_block()
            self.current_block = {"type": "heading", "level": int(tag[1])}
            self.current_block_fragments = []
            return
        if tag in {"ul", "ol"}:
            self.flush_current_block()
            self.list_items = []
            return
        if tag == "li":
            self.current_li_fragments = []
            return
        if tag == "img":
            src = resolve_url(attrs.get("src", ""), self.base_url)
            if src:
                self.blocks.append({
                    "type": "image",
                    "src": src,
                    "alt": attrs.get("alt", ""),
                    "caption": attrs.get("title", "") or attrs.get("alt", ""),
                })
                if self.figure_depth > 0:
                    self.figure_image_index = len(self.blocks) - 1
            return
        if tag == "iframe":
            src = resolve_url(attrs.get("src", ""), self.base_url)
            if src:
                provider = "youtube" if "youtube.com" in src or "youtu.be" in src else "embed"
                self.blocks.append({
                    "type": "embed",
                    "provider": provider,
                    "src": src,
                    "title": attrs.get("title", "Embedded media") or "Embedded media",
                })
            return
        if tag == "br":
            self.append_fragment("<br>")
            return
        if tag in INLINE_ALLOWED:
            self.push_inline_start(tag, attrs)

    def handle_endtag(self, tag: str):
        tag = tag.lower()

        if tag in IGNORED_TAGS:
            if self.ignore_depth > 0:
                self.ignore_depth -= 1
            return

        if not self.is_capturing() and tag not in {self.preferred_root, "body"}:
            if tag == "body" and self.body_depth > 0:
                self.body_depth -= 1
            if tag == self.preferred_root and self.root_depth > 0:
                self.root_depth -= 1
            return

        if tag == "figcaption":
            if self.current_figcaption is not None and self.figure_image_index is not None and 0 <= self.figure_image_index < len(self.blocks):
                caption = normalize_space(re.sub(r"<[^>]+>", "", "".join(self.current_figcaption))).strip()
                if caption and self.blocks[self.figure_image_index].get("type") == "image":
                    self.blocks[self.figure_image_index]["caption"] = caption
            self.current_figcaption = None
        elif tag == "figure":
            if self.figure_depth > 0:
                self.figure_depth -= 1
            if self.figure_depth == 0:
                self.figure_image_index = None
        elif tag == "p":
            self.flush_current_block()
        elif re.fullmatch(r"h[1-6]", tag):
            self.flush_current_block()
        elif tag == "li":
            if self.current_li_fragments is not None and self.list_items is not None:
                item_html = normalize_space("".join(self.current_li_fragments)).strip()
                if item_html:
                    self.list_items.append(item_html)
            self.current_li_fragments = None
        elif tag in {"ul", "ol"}:
            if self.list_items:
                self.blocks.append({"type": "list", "items": self.list_items})
            self.list_items = None
        elif tag in INLINE_ALLOWED:
            self.push_inline_end(tag)

        if tag == self.preferred_root and self.root_depth > 0:
            self.root_depth -= 1
        if tag == "body" and self.body_depth > 0:
            self.body_depth -= 1

    def handle_data(self, data: str):
        if not self.is_capturing():
            return
        if not data:
            return
        self.append_fragment(escape(data))


def extract_json_ld_primary_image(text: str, base_url: str | None) -> dict | None:
    for match in re.finditer(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', text, re.IGNORECASE | re.DOTALL):
        raw = match.group(1).strip()
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except Exception:
            continue

        nodes = []
        if isinstance(payload, dict) and isinstance(payload.get("@graph"), list):
            nodes.extend([node for node in payload["@graph"] if isinstance(node, dict)])
        if isinstance(payload, dict):
            nodes.append(payload)
        elif isinstance(payload, list):
            nodes.extend([node for node in payload if isinstance(node, dict)])

        image_map: dict[str, dict] = {}
        for node in nodes:
            if node.get("@type") == "ImageObject" and node.get("@id"):
                image_map[str(node.get("@id"))] = node

        for node in nodes:
            node_type = str(node.get("@type") or "")
            if node_type not in {"NewsArticle", "Article", "BlogPosting"}:
                continue
            image = node.get("image")
            image_url = ""
            caption = ""
            if isinstance(image, str):
                image_url = image
            elif isinstance(image, dict):
                if image.get("@id") and image.get("@id") in image_map:
                    image = image_map[image.get("@id")]
                image_url = str(image.get("url") or image.get("contentUrl") or "")
                caption = str(image.get("caption") or "")
            if isinstance(image, dict) and image.get("@id") and not image_url:
                ref = image_map.get(str(image.get("@id")))
                if ref:
                    image_url = str(ref.get("url") or ref.get("contentUrl") or "")
                    caption = str(ref.get("caption") or caption or "")
            if image_url:
                return {
                    "type": "image",
                    "src": resolve_url(image_url, base_url),
                    "alt": caption or title or "",
                    "caption": caption or "",
                }
    return None


def parse_html_blocks(text: str, base_url: str | None, title: str | None = None) -> list[dict]:
    fragment = find_best_html_fragment(text, title=title)
    parser = DetailHTMLParser(base_url=base_url, title=title, preferred_root="document")
    parser.feed(fragment)
    parser.flush_current_block()
    blocks = prune_boilerplate_blocks(parser.blocks, title=title)

    primary_image = extract_json_ld_primary_image(text, base_url=base_url)
    has_image = any(block.get("type") == "image" for block in blocks)
    if primary_image and not has_image:
        blocks.insert(0, primary_image)

    return blocks


def detect_source(spec: dict, source_override: str | None, source_cache_dir: Path, cache_html: bool, dry_run: bool) -> Path:
    if source_override:
        path = Path(source_override).resolve()
        if not path.exists():
            raise SystemExit(f"Source file not found: {path}")
        return path

    slug = spec.get("slug") or slugify(spec.get("title") or "")
    candidates = [
        source_cache_dir / f"{slug}.md",
        source_cache_dir / f"{slug}.markdown",
        source_cache_dir / f"{slug}.html",
        source_cache_dir / f"{slug}.htm",
        source_cache_dir / f"{slug}.txt",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()

    if cache_html and spec.get("url"):
        target = source_cache_dir / f"{slug}.html"
        if not dry_run:
            request = urllib.request.Request(spec["url"], headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=45) as response:
                payload = response.read()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        return target.resolve()

    raise SystemExit(f"No cached source found for slug '{slug}'. Looked under {source_cache_dir}.")


def build_detail_payload(spec: dict, blocks: list[dict], args: argparse.Namespace, source_path: Path) -> dict:
    translated_from = args.translated_from or spec.get("url") or source_path.as_uri()
    source_name = args.source_name or spec.get("source") or source_path.name
    source_text = ""
    if source_path.exists():
        source_text = source_path.read_text(encoding="utf-8", errors="ignore")[:12000]
    classification = classify_web_content(title=spec.get("title"), text=source_text)
    if classification == "challenge":
        return build_blocked_detail(
            url=translated_from,
            source_name=source_name,
            message="当前缓存内容仍是站点反爬/挑战页，尚未获得可靠正文；因此只保留草稿入口，不生成可发布 detail。",
        )
    return {
        "available": bool(args.enable_detail and blocks),
        "layout": args.layout,
        "translatedFrom": translated_from,
        "sourceName": source_name,
        "sourceDescription": args.source_description,
        "blocks": blocks,
    }


def main() -> int:
    args = parse_args()
    spec_path = Path(args.spec).resolve()
    source_cache_dir = Path(args.source_cache_dir).resolve()
    output_dir = Path(args.output_dir).resolve()

    spec = load_json(spec_path)
    if not isinstance(spec, dict):
        raise SystemExit("Spec JSON must be an object.")

    source_path = detect_source(spec, args.source, source_cache_dir, args.cache_html, args.dry_run)

    text = source_path.read_text(encoding="utf-8", errors="ignore") if source_path.exists() else ""
    suffix = source_path.suffix.lower()
    base_url = spec.get("url") or None

    if suffix in {".md", ".markdown", ".txt"}:
        blocks = parse_markdown_blocks(text, base_url=base_url, title=spec.get("title"))
    elif suffix in {".html", ".htm"}:
        blocks = parse_html_blocks(text, base_url=base_url, title=spec.get("title"))
    else:
        raise SystemExit(f"Unsupported source format: {suffix}")

    detail_payload = build_detail_payload(spec, blocks, args, source_path)

    output_path = Path(args.output).resolve() if args.output else output_dir / f"{spec.get('slug') or slugify(spec.get('title') or '')}.detail.json"
    write_json(output_path, detail_payload, dry_run=args.dry_run)

    if args.write_spec:
        updated = dict(spec)
        updated["detail"] = detail_payload
        write_json(spec_path, updated, dry_run=args.dry_run)

    print(json.dumps({
        "spec": str(spec_path),
        "source": str(source_path),
        "output": str(output_path),
        "block_count": len(blocks),
        "detail_available": detail_payload.get("available"),
        "write_spec": bool(args.write_spec),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
