#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

from rss_workflow_utils import (
    build_blocked_detail,
    choose_preferred_title,
    classify_web_content,
    is_suspicious_title,
    normalize_space,
    slugify,
)

WORKSPACE = Path("/home/node/.openclaw/workspace")
SITE_ROOT = WORKSPACE / "pi-blog-demo"
DEFAULT_UPSERT_SCRIPT = SITE_ROOT / "tools" / "upsert_post_from_spec.py"
DEFAULT_ARTICLES = SITE_ROOT / "articles.json"
DEFAULT_OUT_DIR = SITE_ROOT / "tools" / "generated-specs"
DEFAULT_CACHE_DIR = SITE_ROOT / "source-cache"
USER_AGENT = "OpenClaw Bundle Spec Builder/1.0"


SOURCE_TAG_HINTS = {
    "the new stack": ["Infrastructure"],
    "cloudflare blog": ["Infrastructure"],
    "simon willison": ["AI", "Tools"],
    "cnx software": ["Hardware"],
    "hackaday": ["Hardware"],
    "servethehome": ["Hardware", "Infrastructure"],
    "lucumr": ["AI", "Agents"],
    "liliputing": ["Hardware", "Laptop"],
}

KEYWORD_TAG_HINTS = [
    (["ai", "llm", "large language model", "prompt", "context rot", "genai"], ["AI"]),
    (["agent", "agents"], ["Agents"]),
    (["code", "coding", "developer", "devtool", "repo", "cursor", "github"], ["DevTools"]),
    (["security", "vulnerability", "scanner", "smuggling", "exploit", "attack", "threat"], ["Security"]),
    (["api", "apis"], ["API"]),
    (["network", "pingora", "sase", "http", "edge"], ["Networking", "Infrastructure"]),
    (["postgres", "database", "vector database", "sql"], ["Postgres", "Data"]),
    (["bluetooth", "soc", "microcontroller", "nrf", "embedded", "iot"], ["Hardware", "Embedded", "IoT"]),
    (["observability", "monitoring", "telemetry", "tracing"], ["Observability"]),
    (["laptop", "notebook", "ultrabook", "panther lake", "ryzen ai"], ["Laptop", "Mobile"]),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate pi-blog-demo post spec JSON files from _hourly_brief_bundle.py output, and optionally upsert them into articles.json."
    )
    parser.add_argument("--bundle", default="-", help="Path to bundle JSON, or '-' for stdin.")
    parser.add_argument("--id", action="append", dest="ids", type=int, help="Select one article id from the bundle. Repeatable.")
    parser.add_argument("--url", action="append", dest="urls", help="Select one article URL from the bundle. Repeatable.")
    parser.add_argument("--all-items", action="store_true", help="Generate specs for all bundle items, not just focus_items.")
    parser.add_argument("--limit", type=int, help="Limit how many selected items to emit.")
    parser.add_argument("--output", help="Output path for a single generated spec.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Directory for generated spec files.")
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR), help="Directory for cached source html/metadata files.")
    parser.add_argument("--cache-html", action="store_true", help="Cache the raw HTML page under source-cache/<slug>.html.")
    parser.add_argument("--cache-metadata", action="store_true", help="Write source-cache/<slug>.metadata.json for future detail generation.")
    parser.add_argument("--upsert", action="store_true", help="After generating spec files, invoke upsert_post_from_spec.py for each one.")
    parser.add_argument("--upsert-script", default=str(DEFAULT_UPSERT_SCRIPT), help="Path to upsert_post_from_spec.py.")
    parser.add_argument("--articles", default=str(DEFAULT_ARTICLES), help="Path to target articles.json.")
    parser.add_argument("--append-new", action="store_true", help="Pass --append-new through to the upsert script.")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without writing files.")
    return parser.parse_args()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_bundle(path_value: str):
    if path_value == "-":
        raw = sys.stdin.read()
        if not raw.strip():
            raise SystemExit("No JSON received on stdin.")
        return json.loads(raw)
    return load_json(Path(path_value).resolve())


def iso_date(value: str | None) -> str:
    text = normalize_space(value)
    if not text:
        return ""
    if len(text) >= 10:
        return text[:10]
    return text


def unique_items(items: list[dict]) -> list[dict]:
    result = []
    seen = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        key = (item.get("id"), item.get("url"))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def collect_items(bundle: dict, use_all_items: bool = False) -> tuple[list[dict], list[dict]]:
    focus_items = bundle.get("focus_items") or []
    other_items = bundle.get("other_items") or []
    all_items = bundle.get("items") or []

    if not all_items:
        all_items = unique_items([*focus_items, *other_items])
    else:
        all_items = unique_items(all_items)

    focus_items = unique_items(focus_items)
    other_items = unique_items(other_items)

    selected = all_items if use_all_items else (focus_items or all_items)
    return selected, all_items


def find_probe(bundle: dict, url: str) -> dict | None:
    for probe in bundle.get("probes") or []:
        if isinstance(probe, dict) and probe.get("url") == url:
            return probe
    return None


def infer_tags(source: str, title: str, description: str) -> list[str]:
    haystack = f"{source} {title} {description}".casefold()
    tags: list[str] = []

    for tag in SOURCE_TAG_HINTS.get(source.casefold(), []):
        if tag not in tags:
            tags.append(tag)

    for keywords, suggested_tags in KEYWORD_TAG_HINTS:
        if any(keyword in haystack for keyword in keywords):
            for tag in suggested_tags:
                if tag not in tags:
                    tags.append(tag)

    if not tags:
        tags.append("Reading")

    return tags[:4]




def format_tag_boxes(tags: list[str]) -> str:
    if not tags:
        return "【Reading】"
    return "".join([f"【{tag}】" for tag in tags])


def ensure_min_length(text: str, minimum: int = 100) -> str:
    if len(text) >= minimum:
        return text
    filler = "整体采用叙事方式串联背景、要点与意义，便于读者在较短时间内把握文章主旨，并为后续深入阅读原文打下基础。"
    extra = "阅读时可重点关注关键数据、技术路线与应用边界，这些信息有助于判断其在实际场景中的价值与限制。"
    combined = text + "" + filler
    if len(combined) < minimum:
        combined = combined + "" + extra
    return combined


def build_summary_text(title: str, source: str, description: str, tags: list[str], challenge: bool = False) -> str:
    if challenge:
        base = (
            f"文章围绕《{title}》展开，但当前抓取命中反爬/挑战页，尚未获得可靠正文。"
            "因此本轮仅保留索引与链接入口，等待后续补全正文与细节。"
            "在未确认内容前不生成逐段详情，以避免把挑战页误当正文。"
        )
        return ensure_min_length(base, 100)

    bits = []
    if title:
        bits.append(f"文章围绕《{title}》展开，结合{source}的发布语境梳理核心主题与背景。")
    if description:
        bits.append(f"页面摘要提到：{description}")
    else:
        bits.append("目前只拿到标题与基础元信息，正文要点需在后续抓取后补齐。")
    bits.append("内容侧重概念梳理与现状观察，并补充可操作的理解路径与注意事项。")
    bits.append("整体采用叙事方式串联背景、要点与意义，便于读者在较短时间内把握文章主旨。")
    return ensure_min_length("".join(bits), 100)

def build_excerpt(title: str, description: str, tags: list[str], source: str, challenge: bool = False) -> str:
    category = format_tag_boxes(tags)
    summary = build_summary_text(title, source, description, tags, challenge=challenge)
    title_line = f"# {title}" if title else "# 未命名文章"
    return f"{title_line}\n\n### 内容分类\n{category}\n\n### 内容总结\n{summary}"


def build_importance_paragraph(tags: list[str]) -> str:
    tag_set = set(tags)
    if "AI" in tag_set and "Agents" in tag_set:
        return "从趋势上看，这类文章值得关注的点在于 AI 正在从一次性回答工具，进一步走向可持续嵌入工作流的执行层。"
    if "AI" in tag_set and "Security" in tag_set:
        return "这类主题的关键不只在模型能力本身，还在于 AI 如何进入原本依赖规则和人工分析的安全流程。"
    if "Security" in tag_set:
        return "如果后续补齐详情视图，重点应继续展开风险边界、漏洞触发条件、检测方式以及修复路径。"
    if "Infrastructure" in tag_set:
        return "如果后续补齐详情视图，重点可以继续展开架构取舍、生产约束、性能代价和工程实施方式。"
    if "Hardware" in tag_set:
        return "如果后续补齐详情视图，重点可以继续展开芯片规格、接口能力、功耗指标和适用场景。"
    return "如果后续补齐详情视图，可以继续沿着原文结构展开关键论点、案例、约束条件与结论。"


def build_summary_content(source: str, description: str, published_at: str, tags: list[str], title: str, challenge: bool = False) -> list[dict]:
    category = format_tag_boxes(tags)
    summary = build_summary_text(title, source, description, tags, challenge=challenge)
    return [
        {
            "heading": "总结",
            "paragraphs": [
                f"# {title}",
                f"### 内容分类\n{category}",
                f"### 内容总结\n{summary}",
            ],
        }
    ]


def build_spec(item: dict, bundle: dict) -> dict:
    url = normalize_space(item.get("url"))
    probe = find_probe(bundle, url) or {}

    item_title = normalize_space(item.get("title"))
    probe_title = normalize_space(probe.get("title"))
    title = choose_preferred_title(item_title, probe_title)
    source = normalize_space(item.get("blog"))
    description = normalize_space(probe.get("description"))
    content_class = classify_web_content(title=probe_title or item_title, text=f"{probe_title}\n{description}")
    challenge = content_class == "challenge"
    published_at = iso_date(item.get("published") or item.get("discovered"))
    slug = slugify(title)
    tags = infer_tags(source, title, description)

    spec = {
        "slug": slug,
        "title": title,
        "author": source,
        "publishedAt": published_at,
        "source": source,
        "url": url,
        "tags": tags,
        "excerpt": build_excerpt(title, description, tags, source, challenge=challenge),
        "content": build_summary_content(source, description, published_at, tags, title, challenge=challenge),
        "detail": {
            "available": False,
        },
        "workflow": {
            "articleId": item.get("id"),
            "Title": item_title,
        },
    }

    if challenge:
        spec["detail"] = build_blocked_detail(
            url=url,
            source_name=source,
            message="当前自动抓取命中了站点反爬/挑战页，尚未获得可靠正文；本轮只保留草稿入口，等待后续重试。",
        )
        spec.setdefault("workflow", {})["blockedBy"] = content_class
        spec["workflow"]["probeTitle"] = probe_title
    elif probe_title and is_suspicious_title(probe_title):
        spec.setdefault("workflow", {})["probeTitleRejected"] = probe_title

    return spec


def select_items(bundle: dict, args: argparse.Namespace) -> list[dict]:
    selected, all_items = collect_items(bundle, use_all_items=args.all_items)
    by_id = {int(item.get("id")): item for item in all_items if item.get("id") is not None}
    by_url = {str(item.get("url")): item for item in all_items if item.get("url")}

    if args.ids:
        items = []
        missing = []
        for item_id in args.ids:
            item = by_id.get(int(item_id))
            if item is None:
                missing.append(str(item_id))
            else:
                items.append(item)
        if missing:
            raise SystemExit(f"Bundle does not contain article id(s): {', '.join(missing)}")
        selected = unique_items(items)

    if args.urls:
        items = []
        missing = []
        for url in args.urls:
            item = by_url.get(url)
            if item is None:
                missing.append(url)
            else:
                items.append(item)
        if missing:
            raise SystemExit("Bundle does not contain article URL(s): " + ", ".join(missing))
        selected = unique_items(items)

    if args.limit is not None:
        selected = selected[: max(args.limit, 0)]

    if not selected:
        raise SystemExit("No articles selected from the bundle.")

    return selected


def write_json(path: Path, payload, dry_run: bool = False) -> None:
    if dry_run:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def cache_metadata(path: Path, item: dict, probe: dict | None, dry_run: bool = False) -> None:
    classification = classify_web_content(
        title=(probe or {}).get("title") or item.get("title"),
        text=f"{(probe or {}).get('title') or ''}\n{(probe or {}).get('description') or ''}",
    )
    payload = {
        "item": item,
        "probe": probe or {},
        "classification": classification,
    }
    write_json(path, payload, dry_run=dry_run)


def fetch_url_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        return response.read()


def cache_html(path: Path, url: str, dry_run: bool = False) -> None:
    if dry_run:
        return
    payload = fetch_url_bytes(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def run_upsert(spec_path: Path, args: argparse.Namespace) -> tuple[bool, str]:
    cmd = [
        "python3",
        str(Path(args.upsert_script).resolve()),
        "--spec",
        str(spec_path.resolve()),
        "--articles",
        str(Path(args.articles).resolve()),
    ]
    if args.append_new:
        cmd.append("--append-new")
    if args.dry_run:
        cmd.append("--dry-run")

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    output = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    return proc.returncode == 0, output.strip()


def main() -> int:
    args = parse_args()
    bundle = read_bundle(args.bundle)
    items = select_items(bundle, args)

    output_path = Path(args.output).resolve() if args.output else None
    out_dir = Path(args.out_dir).resolve()
    cache_dir = Path(args.cache_dir).resolve()

    if output_path and len(items) != 1:
        raise SystemExit("--output can only be used when exactly one article is selected.")

    summary = {
        "selected_count": len(items),
        "generated": [],
        "cached": [],
        "upserts": [],
    }

    for item in items:
        spec = build_spec(item, bundle)
        slug = spec["slug"]
        url = spec["url"]
        probe = find_probe(bundle, url)

        spec_path = output_path or (out_dir / f"{slug}.json")
        write_json(spec_path, spec, dry_run=args.dry_run)
        summary["generated"].append({
            "id": item.get("id"),
            "slug": slug,
            "spec": str(spec_path),
            "challenge_blocked": bool(((spec.get("workflow") or {}).get("blockedBy") == "challenge")),
        })

        if args.cache_metadata:
            metadata_path = cache_dir / f"{slug}.metadata.json"
            cache_metadata(metadata_path, item=item, probe=probe, dry_run=args.dry_run)
            summary["cached"].append({"type": "metadata", "path": str(metadata_path)})

        if args.cache_html and url:
            html_path = cache_dir / f"{slug}.html"
            try:
                cache_html(html_path, url, dry_run=args.dry_run)
                summary["cached"].append({"type": "html", "path": str(html_path)})
            except Exception as exc:
                summary.setdefault("warnings", []).append({
                    "slug": slug,
                    "type": "cache_html_failed",
                    "detail": repr(exc),
                })

        if args.upsert:
            ok, output = run_upsert(spec_path, args)
            summary["upserts"].append({
                "slug": slug,
                "ok": ok,
                "output": output,
            })

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
