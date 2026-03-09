#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path


WORKSPACE = Path("/home/node/.openclaw/workspace")
SITE_ROOT = WORKSPACE / "pi-blog-demo"
DEFAULT_UPSERT_SCRIPT = SITE_ROOT / "tools" / "upsert_post_from_spec.py"
DEFAULT_ARTICLES = SITE_ROOT / "articles.json"
DEFAULT_OUT_DIR = SITE_ROOT / "tools" / "generated-specs"
DEFAULT_CACHE_DIR = SITE_ROOT / "source-cache"
USER_AGENT = "OpenClaw RSS Bundle Spec Builder/1.0"


SOURCE_TAG_HINTS = {
    "the new stack": ["Infrastructure"],
    "cloudflare blog": ["Infrastructure"],
    "simon willison": ["AI", "Tools"],
    "cnx software": ["Hardware"],
    "hackaday": ["Hardware"],
    "servethehome": ["Hardware", "Infrastructure"],
    "lucumr": ["AI", "Agents"],
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
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate pi-blog-demo post spec JSON files from rss_hourly_brief_bundle.py output, and optionally upsert them into articles.json."
    )
    parser.add_argument("--bundle", default="-", help="Path to bundle JSON, or '-' for stdin.")
    parser.add_argument("--id", action="append", dest="ids", type=int, help="Select one article id from the bundle. Repeatable.")
    parser.add_argument("--url", action="append", dest="urls", help="Select one article URL from the bundle. Repeatable.")
    parser.add_argument("--all-items", action="store_true", help="Generate specs for all bundle items, not just focus_items.")
    parser.add_argument("--limit", type=int, help="Limit how many selected items to emit.")
    parser.add_argument("--output", help="Output path for a single generated spec.")
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Directory for generated spec files.")
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


def slugify(text: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value or "post"


def normalize_space(text: str | None) -> str:
    value = str(text or "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


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


def build_excerpt(title: str, description: str) -> str:
    if description:
        shortened = description.strip()
        if len(shortened) > 140:
            shortened = shortened[:137].rstrip() + "..."
        return f"这篇文章围绕“{title}”展开，RSS 摘要提到：{shortened}"
    return f"这篇文章围绕“{title}”展开，当前已从 RSS 条目同步到静态博客工作流中。"


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


def build_summary_content(source: str, description: str, published_at: str, tags: list[str]) -> list[dict]:
    paragraphs = []
    if description:
        paragraphs.append(f"基于 RSS 摘要与页面元数据，原文重点是：{description}")
    else:
        paragraphs.append("当前只拿到了标题、来源和链接，还没有更完整的页面摘要，因此这里只生成一个可继续加工的草稿入口。")

    meta_bits = [bit for bit in [source, published_at] if bit]
    if meta_bits:
        paragraphs.append(f"来源信息：{'｜'.join(meta_bits)}。")

    return [
        {
            "heading": "文章核心",
            "paragraphs": paragraphs,
        },
        {
            "heading": "值得继续补充的点",
            "paragraphs": [
                build_importance_paragraph(tags),
                "当前 spec 主要用于把 RSS 条目先落成静态站文章入口；如果后续抓到更完整正文，再补 detail.blocks[]。",
            ],
        },
    ]


def build_spec(item: dict, bundle: dict) -> dict:
    url = normalize_space(item.get("url"))
    probe = find_probe(bundle, url) or {}

    title = normalize_space(probe.get("title") or item.get("title"))
    source = normalize_space(item.get("blog"))
    description = normalize_space(probe.get("description"))
    published_at = iso_date(item.get("published") or item.get("discovered"))
    slug = slugify(title)
    tags = infer_tags(source, title, description)

    return {
        "slug": slug,
        "title": title,
        "author": "",
        "publishedAt": published_at,
        "source": source,
        "url": url,
        "tags": tags,
        "excerpt": build_excerpt(title, description),
        "content": build_summary_content(source, description, published_at, tags),
        "detail": {
            "available": False,
        },
    }


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
    payload = {
        "item": item,
        "probe": probe or {},
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
    cache_dir = DEFAULT_CACHE_DIR.resolve()

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
