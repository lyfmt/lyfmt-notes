#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import pty
import re
import select
import subprocess
import sys
import time
from copy import deepcopy
from pathlib import Path


WORKSPACE = Path("/home/node/.openclaw/workspace")
SITE_ROOT = WORKSPACE / "pi-blog-demo"
DEFAULT_OUTPUT_DIR = SITE_ROOT / "tools" / "generated-details"
DEFAULT_LAYOUT = "detail-zh"
DEFAULT_SOURCE_DESCRIPTION = "以下为根据原文结构整理的中文细读版，保留原文段落推进与媒体顺序；内容为中文改写/细读，不是逐字镜像。"
ALLOWED_INLINE_TAGS = {"a", "em", "strong", "code", "br", "sup", "sub", "span"}
TAG_PLACEHOLDER_RE = re.compile(r"__HTML_TAG_(\d+)__")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refine English detail.blocks[] into a Chinese close-reading detail draft using local Pi CLI."
    )
    parser.add_argument("--spec", required=True, help="Path to post spec JSON.")
    parser.add_argument("--detail", help="Optional input detail JSON path. Defaults to spec.detail.")
    parser.add_argument("--output", help="Path to write the Chinese detail JSON.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Directory for generated Chinese detail drafts.")
    parser.add_argument("--write-spec", action="store_true", help="Write the generated Chinese detail back into the spec JSON.")
    parser.add_argument("--enable-detail", action="store_true", help="Set detail.available=true when writing output.")
    parser.add_argument("--layout", default=DEFAULT_LAYOUT, help=f"detail.layout value (default: {DEFAULT_LAYOUT})")
    parser.add_argument("--source-description", default=DEFAULT_SOURCE_DESCRIPTION, help="detail.sourceDescription value.")
    parser.add_argument("--pi-bin", default="pi", help="Pi CLI binary (default: pi)")
    parser.add_argument("--timeout-seconds", type=int, default=180, help="Timeout per Pi invocation (default: 180)")
    parser.add_argument("--start-index", type=int, default=0, help="Start refining from this block index (0-based).")
    parser.add_argument("--limit", type=int, default=0, help="Only refine this many blocks after start-index (0 means all).")
    parser.add_argument("--force", action="store_true", help="Refine blocks even if they already look Chinese.")
    parser.add_argument("--continue-on-error", action="store_true", help="Keep the original block when one refinement call fails.")
    parser.add_argument("--checkpoint-every", type=int, default=1, help="Write output checkpoint every N processed blocks (default: 1).")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without writing files.")
    return parser.parse_args()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


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


def normalize_space(value: str | None) -> str:
    text = str(value or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


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


INLINE_TAG_RE = re.compile(r"</?(?:a|em|strong|code|br|sup|sub|span)\b[^>]*?/?>", re.IGNORECASE)
UNSAFE_TAG_RE = re.compile(r"<(?!(?:/?(?:a|em|strong|code|br|sup|sub|span)\b))[^>]+>", re.IGNORECASE)


def freeze_inline_html(text: str) -> tuple[str, dict[str, str]]:
    mapping: dict[str, str] = {}
    counter = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal counter
        counter += 1
        token = f"__HTML_TAG_{counter}__"
        mapping[token] = match.group(0)
        return token

    frozen = INLINE_TAG_RE.sub(replace, text or "")
    return frozen, mapping


def restore_inline_html(text: str, mapping: dict[str, str]) -> str:
    restored = str(text or "")
    for token, tag in mapping.items():
        restored = restored.replace(token, tag)
    restored = UNSAFE_TAG_RE.sub("", restored)
    return restored


def extract_json_object(text: str) -> str:
    raw = text.strip()
    if not raw:
        raise ValueError("Empty Pi output.")

    try:
        json.loads(raw)
        return raw
    except Exception:
        pass

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"Could not find JSON object in Pi output: {raw[:240]}")
    candidate = match.group(0)
    json.loads(candidate)
    return candidate


def run_pi_json(prompt: str, pi_bin: str, timeout_seconds: int) -> dict:
    master_fd, slave_fd = pty.openpty()
    process = subprocess.Popen(
        [pi_bin, "-p", prompt],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        text=False,
        close_fds=True,
    )
    os.close(slave_fd)

    chunks: list[bytes] = []
    deadline = time.time() + timeout_seconds
    try:
        while True:
            if time.time() > deadline:
                process.kill()
                raise TimeoutError(f"Pi invocation timed out after {timeout_seconds}s")

            if process.poll() is not None:
                while True:
                    ready, _, _ = select.select([master_fd], [], [], 0)
                    if master_fd not in ready:
                        break
                    try:
                        data = os.read(master_fd, 65536)
                    except OSError:
                        data = b""
                    if not data:
                        break
                    chunks.append(data)
                break

            ready, _, _ = select.select([master_fd], [], [], 0.25)
            if master_fd in ready:
                try:
                    data = os.read(master_fd, 65536)
                except OSError:
                    data = b""
                if data:
                    chunks.append(data)
    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)

    output = b"".join(chunks).decode("utf-8", errors="ignore").strip()
    if process.returncode != 0:
        raise RuntimeError(f"Pi exited with code {process.returncode}: {output[:400]}")
    payload = extract_json_object(output)
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Pi output must be a JSON object.")
    return data


def build_block_prompt(block: dict, context: dict) -> str:
    article_title = context.get("title") or ""
    source_name = context.get("source") or ""
    current_heading = context.get("current_heading") or ""
    frozen_payload = json.dumps(block, ensure_ascii=False)

    return f"""你是静态博客详情页导入器的一部分。
你的任务：把一个原文 detail block 改写成适合中文博客“详情 / 细读”页的中文版本。

硬性要求：
1. 这不是逐字翻译镜像，而是中文改写 / 细读；必须忠实保留原意、结构和信息密度。
2. 输出必须是单个 JSON 对象，不要代码块，不要解释。
3. 必须保留 block 的 type；heading 保留 level；image/embed 保留 src/provider 等媒体字段。
4. 如果字段里出现 __HTML_TAG_n__ 这样的占位符，必须原样保留，不能改写、删除或重排。
5. 不要新增任何 HTML 标签；只允许保留输入里已有的占位符位置。
6. 专有名词、人名、产品名、公司名可以保留英文或中英混写，但整体表达必须是自然中文。
7. 风格是“中文细读版”：更适合中文读者阅读，可稍作重述，但不要加入原文没有的新事实。
8. 如果输入已经明显是中文，只做轻微润色或原样返回即可。

上下文：
- 文章标题：{article_title}
- 来源：{source_name}
- 当前小节：{current_heading}

输入 block JSON：
{frozen_payload}
"""


def refine_html_block(block: dict, context: dict, pi_bin: str, timeout_seconds: int) -> dict:
    refined = deepcopy(block)
    html_value = str(block.get("html") or "")
    frozen_html, mapping = freeze_inline_html(html_value)
    payload = {"type": block.get("type"), "html": frozen_html}
    if "level" in block:
        payload["level"] = block.get("level")
    result = run_pi_json(build_block_prompt(payload, context), pi_bin=pi_bin, timeout_seconds=timeout_seconds)
    refined["html"] = restore_inline_html(str(result.get("html") or frozen_html), mapping)
    return refined


def refine_heading_block(block: dict, context: dict, pi_bin: str, timeout_seconds: int) -> dict:
    payload = {"type": "heading", "level": block.get("level", 2), "text": str(block.get("text") or "")}
    result = run_pi_json(build_block_prompt(payload, context), pi_bin=pi_bin, timeout_seconds=timeout_seconds)
    return {
        "type": "heading",
        "level": int(result.get("level") or block.get("level") or 2),
        "text": normalize_space(result.get("text") or block.get("text") or ""),
    }


def refine_list_block(block: dict, context: dict, pi_bin: str, timeout_seconds: int) -> dict:
    items = []
    mappings: list[dict[str, str]] = []
    for item in (block.get("items") or []):
        frozen_item, mapping = freeze_inline_html(str(item or ""))
        items.append(frozen_item)
        mappings.append(mapping)

    payload = {"type": "list", "items": items}
    result = run_pi_json(build_block_prompt(payload, context), pi_bin=pi_bin, timeout_seconds=timeout_seconds)
    output_items = result.get("items") if isinstance(result.get("items"), list) else items

    restored_items = []
    for index, original in enumerate(items):
        candidate = str(output_items[index] if index < len(output_items) else original)
        restored_items.append(restore_inline_html(candidate, mappings[index]))

    return {"type": "list", "items": restored_items}


def refine_image_block(block: dict, context: dict, pi_bin: str, timeout_seconds: int) -> dict:
    text_fields = {
        "alt": str(block.get("alt") or ""),
        "caption": str(block.get("caption") or ""),
    }
    needs_refine = any(value and (not has_cjk(value)) for value in text_fields.values())
    if not needs_refine:
        return deepcopy(block)

    payload = {
        "type": "image",
        "src": block.get("src") or "",
        "alt": text_fields["alt"],
        "caption": text_fields["caption"],
    }
    result = run_pi_json(build_block_prompt(payload, context), pi_bin=pi_bin, timeout_seconds=timeout_seconds)
    refined = deepcopy(block)
    refined["alt"] = normalize_space(result.get("alt") or text_fields["alt"])
    refined["caption"] = normalize_space(result.get("caption") or text_fields["caption"])
    return refined


def refine_embed_block(block: dict, context: dict, pi_bin: str, timeout_seconds: int) -> dict:
    title = str(block.get("title") or "")
    if not title or has_cjk(title):
        return deepcopy(block)

    payload = {
        "type": "embed",
        "provider": block.get("provider") or "embed",
        "src": block.get("src") or "",
        "title": title,
    }
    result = run_pi_json(build_block_prompt(payload, context), pi_bin=pi_bin, timeout_seconds=timeout_seconds)
    refined = deepcopy(block)
    refined["title"] = normalize_space(result.get("title") or title)
    return refined


def refine_block(block: dict, context: dict, pi_bin: str, timeout_seconds: int, force: bool = False) -> dict:
    if not isinstance(block, dict) or not block.get("type"):
        return deepcopy(block)

    block_type = block.get("type")
    if block_type in {"image", "embed"} and not force:
        return deepcopy(block)
    if not force and block_has_cjk(block):
        return deepcopy(block)

    if block_type == "heading":
        return refine_heading_block(block, context, pi_bin, timeout_seconds)
    if block_type in {"paragraph", "footnote"}:
        return refine_html_block(block, context, pi_bin, timeout_seconds)
    if block_type == "list":
        return refine_list_block(block, context, pi_bin, timeout_seconds)
    if block_type == "image":
        return refine_image_block(block, context, pi_bin, timeout_seconds)
    if block_type == "embed":
        return refine_embed_block(block, context, pi_bin, timeout_seconds)
    return deepcopy(block)


def load_detail_from_inputs(spec: dict, detail_path: Path | None) -> dict:
    if detail_path:
        payload = load_json(detail_path)
        if not isinstance(payload, dict):
            raise SystemExit("Detail JSON must be an object.")
        return payload

    detail = spec.get("detail")
    if not isinstance(detail, dict):
        raise SystemExit("Spec does not contain a detail object. Run build_detail_from_cache.py first or pass --detail.")
    return detail


def refine_detail_payload(
    detail: dict,
    spec: dict,
    args: argparse.Namespace,
    checkpoint_path: Path | None = None,
) -> dict:
    blocks = detail.get("blocks")
    if not isinstance(blocks, list):
        raise SystemExit("detail.blocks must be a list.")

    start = max(0, int(args.start_index or 0))
    limit = max(0, int(args.limit or 0))
    end = len(blocks) if limit == 0 else min(len(blocks), start + limit)

    refined_blocks = []
    current_heading = ""
    errors: list[dict] = []
    processed_in_range = 0

    def build_payload_snapshot() -> dict:
        payload = deepcopy(detail)
        payload["available"] = bool(args.enable_detail and refined_blocks)
        payload["layout"] = args.layout
        payload["sourceDescription"] = args.source_description
        payload["blocks"] = refined_blocks
        if errors:
            payload["refineErrors"] = errors
        return payload

    for index, block in enumerate(blocks):
        block_copy = deepcopy(block)
        if block_copy.get("type") == "heading" and block_copy.get("text"):
            current_heading = str(block_copy.get("text") or "")

        if index < start or index >= end:
            refined_blocks.append(block_copy)
            continue

        block_type = str(block_copy.get("type") or "unknown")
        print(f"[refine_detail_to_chinese] block {index + 1}/{len(blocks)} type={block_type}", file=sys.stderr, flush=True)

        context = {
            "title": spec.get("title") or "",
            "source": detail.get("sourceName") or spec.get("source") or "",
            "current_heading": current_heading,
        }

        try:
            refined = refine_block(block_copy, context, args.pi_bin, args.timeout_seconds, force=args.force)
        except Exception as exc:
            if not args.continue_on_error:
                raise
            refined = block_copy
            error_item = {
                "index": index,
                "type": block_type,
                "message": str(exc),
            }
            errors.append(error_item)
            print(
                f"[refine_detail_to_chinese] keep-original block {index + 1}/{len(blocks)} after error: {exc}",
                file=sys.stderr,
                flush=True,
            )

        refined_blocks.append(refined)
        processed_in_range += 1
        if refined.get("type") == "heading" and refined.get("text"):
            current_heading = str(refined.get("text") or current_heading)

        checkpoint_every = max(1, int(args.checkpoint_every or 1))
        if checkpoint_path and processed_in_range % checkpoint_every == 0:
            write_json(checkpoint_path, build_payload_snapshot(), dry_run=args.dry_run)

    return build_payload_snapshot()


def main() -> int:
    args = parse_args()
    spec_path = Path(args.spec).resolve()
    detail_path = Path(args.detail).resolve() if args.detail else None
    output_dir = Path(args.output_dir).resolve()

    spec = load_json(spec_path)
    if not isinstance(spec, dict):
        raise SystemExit("Spec JSON must be an object.")

    detail = load_detail_from_inputs(spec, detail_path)

    slug = spec.get("slug") or slugify(spec.get("title") or "")
    output_path = Path(args.output).resolve() if args.output else output_dir / f"{slug}.zh.detail.json"
    refined_detail = refine_detail_payload(detail, spec, args, checkpoint_path=output_path)
    write_json(output_path, refined_detail, dry_run=args.dry_run)

    if args.write_spec:
        updated_spec = deepcopy(spec)
        updated_spec["detail"] = refined_detail
        write_json(spec_path, updated_spec, dry_run=args.dry_run)

    print(json.dumps({
        "spec": str(spec_path),
        "detail_input": str(detail_path) if detail_path else "spec.detail",
        "output": str(output_path),
        "block_count": len(refined_detail.get("blocks") or []),
        "detail_available": refined_detail.get("available"),
        "write_spec": bool(args.write_spec),
        "range": {"start_index": int(args.start_index or 0), "limit": int(args.limit or 0)},
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
