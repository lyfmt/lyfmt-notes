#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

WORKSPACE = Path("/home/node/.openclaw/workspace")
SITE_ROOT = WORKSPACE / "pi-blog-demo"
DEFAULT_CONFIG_PATH = Path("/home/node/.openclaw/openclaw.json")
DEFAULT_GATEWAY_URL = "http://127.0.0.1:18789/v1/chat/completions"
DEFAULT_AGENT_ID = "gpt52-codex-agent"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate compliant summary (excerpt/content) via OpenClaw main model from detail.blocks."
    )
    parser.add_argument("--spec", required=True, help="Path to post spec JSON.")
    parser.add_argument("--write-spec", action="store_true", help="Write summary back into the spec JSON.")
    parser.add_argument("--output", help="Optional output path for the updated spec JSON.")
    parser.add_argument("--gateway-url", default=DEFAULT_GATEWAY_URL, help="Gateway /v1/chat/completions URL.")
    parser.add_argument("--agent-id", default=DEFAULT_AGENT_ID, help="OpenClaw agent id to target.")
    parser.add_argument("--max-chars", type=int, default=20000, help="Max chars of detail text to send.")
    parser.add_argument("--min-chars", type=int, default=100, help="Minimum characters required for summary.")
    parser.add_argument("--retries", type=int, default=2, help="Retry attempts when summary invalid.")
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "")


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def format_tag_boxes(tags: list[str]) -> str:
    if not tags:
        return "【Reading】"
    return "".join([f"【{tag}】" for tag in tags])


def build_detail_text(detail: dict, max_chars: int) -> str:
    blocks = detail.get("blocks") if isinstance(detail.get("blocks"), list) else []
    parts: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = block.get("type")
        if block_type == "heading":
            text = normalize_space(block.get("text"))
            if text:
                parts.append(f"[H] {text}")
        elif block_type in {"paragraph", "footnote"}:
            html = strip_html(block.get("html") or "")
            text = normalize_space(html)
            if text:
                parts.append(text)
        elif block_type == "list":
            items = [normalize_space(strip_html(item)) for item in (block.get("items") or []) if normalize_space(strip_html(item))]
            if items:
                parts.append("\n".join([f"- {item}" for item in items]))
        elif block_type == "image":
            alt = normalize_space(block.get("alt"))
            caption = normalize_space(block.get("caption"))
            combined = " ".join([value for value in [alt, caption] if value])
            if combined:
                parts.append(f"[Image] {combined}")
        elif block_type == "embed":
            title = normalize_space(block.get("title"))
            if title:
                parts.append(f"[Embed] {title}")
    text = "\n\n".join(parts)
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars]
    return text


def read_gateway_token() -> str:
    token = os.environ.get("OPENCLAW_GATEWAY_TOKEN") or os.environ.get("OPENCLAW_TOKEN")
    if token:
        return token
    if DEFAULT_CONFIG_PATH.exists():
        payload = load_json(DEFAULT_CONFIG_PATH)
        gateway = payload.get("gateway") if isinstance(payload, dict) else {}
        auth = gateway.get("auth") if isinstance(gateway, dict) else {}
        token = auth.get("token") if isinstance(auth, dict) else None
        if token:
            return str(token)
    raise RuntimeError("Gateway token not found (OPENCLAW_GATEWAY_TOKEN or openclaw.json).")


def extract_json_object(text: str) -> dict:
    raw = text.strip()
    if not raw:
        raise ValueError("Empty model response.")
    # Strip code fences if present.
    raw = re.sub(r"^```(?:json)?", "", raw.strip(), flags=re.IGNORECASE).strip()
    raw = re.sub(r"```$", "", raw.strip()).strip()
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model response.")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise ValueError("Model response JSON is not an object.")
    return data


def call_gateway(prompt: str, gateway_url: str, agent_id: str, token: str) -> dict:
    payload = {
        "model": f"openclaw:{agent_id}",
        "messages": [
            {"role": "system", "content": "你是中文技术内容编辑，必须严格按要求输出 JSON。"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        gateway_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "x-openclaw-agent-id": agent_id,
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read().decode("utf-8")
    data = json.loads(raw)
    choices = data.get("choices") if isinstance(data, dict) else None
    if not choices:
        raise RuntimeError(f"Gateway response missing choices: {raw[:400]}")
    content = choices[0].get("message", {}).get("content")
    if not content:
        raise RuntimeError("Gateway response missing message content.")
    return extract_json_object(content)


def build_prompt(title: str, source: str, tags: list[str], detail_text: str, min_chars: int) -> str:
    tags_box = format_tag_boxes(tags)
    return f"""请根据以下中文详情内容生成总结，只能输出 JSON（不要代码块、不要解释）。\n\n硬性要求：\n1) 输出 JSON 字段固定为：title, category, summary。\n2) title 为文章标题（中文或原文均可），不要加前后缀。\n3) category 必须是小框标签格式，如【Java】【AI】；如果没有合适分类，输出【Reading】。\n4) summary 必须为中文叙事段落，字数不少于 {min_chars}，禁止出现“rss/RS S”等字样。\n5) summary 只基于下方详情内容，不得编造或扩写未出现的信息。\n\n参考标签（可选）：{tags_box}\n来源：{source}\n\n标题：{title}\n\n详情内容（可能截断）：\n{detail_text}\n"""


def build_excerpt(title: str, category: str, summary: str) -> tuple[str, list[dict]]:
    title_line = f"# {title}" if title else "# 未命名文章"
    excerpt = f"{title_line}\n\n### 内容分类\n{category}\n\n### 内容总结\n{summary}"
    content = [
        {
            "heading": "总结",
            "paragraphs": [
                title_line,
                f"### 内容分类\n{category}",
                f"### 内容总结\n{summary}",
            ],
        }
    ]
    return excerpt, content


def validate_summary(payload: dict, min_chars: int) -> tuple[bool, str]:
    title = normalize_space(payload.get("title"))
    category = normalize_space(payload.get("category"))
    summary = normalize_space(payload.get("summary"))
    if not title or not category or not summary:
        return False, "missing_fields"
    if re.search(r"rss", summary, re.IGNORECASE):
        return False, "contains_rss"
    if len(summary) < min_chars:
        return False, "summary_too_short"
    if not re.search(r"【.+】", category):
        return False, "invalid_category"
    return True, "ok"


def main() -> int:
    args = parse_args()
    spec_path = Path(args.spec).resolve()
    spec = load_json(spec_path)
    if not isinstance(spec, dict):
        raise SystemExit("Spec JSON must be an object.")

    detail = spec.get("detail") if isinstance(spec.get("detail"), dict) else {}
    detail_text = build_detail_text(detail, args.max_chars)
    if not detail_text.strip():
        raise SystemExit("Detail text is empty; cannot summarize.")

    title = normalize_space(spec.get("title"))
    source = normalize_space(spec.get("source"))
    tags = spec.get("tags") if isinstance(spec.get("tags"), list) else []
    tags = [normalize_space(tag) for tag in tags if normalize_space(tag)]

    token = read_gateway_token()
    prompt = build_prompt(title, source, tags, detail_text, args.min_chars)

    last_error = None
    payload = None
    for attempt in range(max(1, args.retries + 1)):
        payload = call_gateway(prompt, args.gateway_url, args.agent_id, token)
        ok, reason = validate_summary(payload, args.min_chars)
        if ok:
            last_error = None
            break
        last_error = reason
        prompt = build_prompt(title, source, tags, detail_text, args.min_chars + 20)
    if last_error:
        raise SystemExit(f"Model summary invalid: {last_error}")

    title_out = normalize_space(payload.get("title")) or title
    category = normalize_space(payload.get("category"))
    summary = normalize_space(payload.get("summary"))

    excerpt, content = build_excerpt(title_out, category, summary)
    spec["excerpt"] = excerpt
    spec["content"] = content

    output_path = Path(args.output).resolve() if args.output else spec_path
    if args.write_spec or args.output:
        write_json(output_path, spec)

    print(json.dumps({
        "ok": True,
        "spec": str(output_path),
        "title": title_out,
        "category": category,
        "summary_len": len(summary),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
