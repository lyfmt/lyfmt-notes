#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import traceback
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import select
import time

from rss_workflow_utils import (
    atomic_write_json,
    detail_progress,
    find_existing_post,
    load_articles_payload,
    normalize_space,
)

WORKSPACE = Path("/home/node/.openclaw/workspace")
SITE_ROOT = WORKSPACE / "pi-blog-demo"
TOOLS_DIR = SITE_ROOT / "tools"
RUNTIME_DIR = WORKSPACE / ".openclaw" / "runtime" / "rss-autopublish"
RUNS_DIR = RUNTIME_DIR / "runs"
ITEMS_DIR = RUNTIME_DIR / "items"
CURRENT_RUN_PATH = RUNTIME_DIR / "current-run.json"
LATEST_RUN_PATH = RUNTIME_DIR / "latest-run.json"
DEFAULT_BUNDLE_SCRIPT = WORKSPACE / "scripts" / "rss_hourly_brief_bundle.py"
DEFAULT_STATE_SCRIPT = WORKSPACE / "scripts" / "rss_hourly_digest_state.py"
DEFAULT_BUILD_SPEC = TOOLS_DIR / "build_post_spec_from_bundle.py"
DEFAULT_BUILD_DETAIL = TOOLS_DIR / "build_detail_from_cache.py"
DEFAULT_REFINE_DETAIL = TOOLS_DIR / "refine_detail_to_chinese.py"
DEFAULT_UPSERT = TOOLS_DIR / "upsert_post_from_spec.py"
DEFAULT_VALIDATE = TOOLS_DIR / "validate_articles.py"
DEFAULT_ARTICLES = SITE_ROOT / "articles.json"
DEFAULT_SOURCE_CACHE = SITE_ROOT / "source-cache"
DEFAULT_SPEC_DIR = TOOLS_DIR / "generated-specs"
DEFAULT_DETAIL_DIR = TOOLS_DIR / "generated-details"
TERMINAL_OUTCOMES = {"published", "draft_only", "blocked", "skipped_existing", "failed"}
COMMITTABLE_OUTCOMES = {"published"}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return deepcopy(default)
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    atomic_write_json(path, payload)


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def run_command(
    cmd: list[str],
    *,
    cwd: Path,
    timeout: int,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
    heartbeat_seconds: int | None = None,
) -> dict[str, Any]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    started = utc_now()
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            env=merged_env,
            stdin=subprocess.PIPE if input_text is not None else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            stdout_text, stderr_text = proc.communicate(input=input_text, timeout=timeout)
            return {
                "ok": proc.returncode == 0,
                "code": proc.returncode,
                "stdout": _to_text(stdout_text),
                "stderr": _to_text(stderr_text),
                "started_at": started,
                "finished_at": utc_now(),
                "cmd": cmd,
            }
        except subprocess.TimeoutExpired:
            # Optional heartbeat window to keep outer wrappers alive while we wait a bit longer.
            if heartbeat_seconds and heartbeat_seconds > 0:
                deadline = time.time() + heartbeat_seconds
                while time.time() < deadline:
                    ready, _, _ = select.select([proc.stdout, proc.stderr], [], [], 0.25)
                    if ready:
                        break
                    time.sleep(0.25)
            proc.kill()
            stdout_text, stderr_text = proc.communicate()
            return {
                "ok": False,
                "code": None,
                "stdout": _to_text(stdout_text),
                "stderr": _to_text(stderr_text) + f"\nTIMEOUT after {timeout}s",
                "started_at": started,
                "finished_at": utc_now(),
                "cmd": cmd,
                "timeout": timeout,
                "timeout_expired": True,
            }
    except Exception as exc:
        return {
            "ok": False,
            "code": None,
            "stdout": "",
            "stderr": _to_text(exc),
            "started_at": started,
            "finished_at": utc_now(),
            "cmd": cmd,
        }


def tail_lines(text: str, limit: int = 80) -> list[str]:
    lines = [line.rstrip() for line in str(text or "").splitlines() if line.strip()]
    if len(lines) <= limit:
        return lines
    return lines[-limit:]


def parse_json_stdout(result: dict[str, Any]) -> tuple[Any | None, str | None]:
    raw = normalize_space(result.get("stdout"))
    if not raw:
        return None, "empty_stdout"
    try:
        return json.loads(result.get("stdout") or ""), None
    except Exception as exc:
        return None, repr(exc)


def item_state_path(article_id: int) -> Path:
    return ITEMS_DIR / f"{article_id}.json"


def load_item_state(article_id: int) -> dict[str, Any]:
    state = read_json(item_state_path(article_id), default={})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("article_id", int(article_id))
    state.setdefault("attempts", [])
    state.setdefault("history", [])
    state.setdefault("retry_count", 0)
    return state


def save_item_state(article_id: int, payload: dict[str, Any]) -> None:
    payload["updated_at"] = utc_now()
    write_json(item_state_path(article_id), deepcopy(payload))


def summarize_result(result: dict[str, Any], stdout_lines: int = 40, stderr_lines: int = 40) -> dict[str, Any]:
    return {
        "ok": bool(result.get("ok")),
        "code": result.get("code"),
        "timeout": bool(result.get("timeout_expired")),
        "stdout_tail": tail_lines(result.get("stdout") or "", stdout_lines),
        "stderr_tail": tail_lines(result.get("stderr") or "", stderr_lines),
        "started_at": result.get("started_at"),
        "finished_at": result.get("finished_at"),
        "cmd": result.get("cmd"),
    }


def stage_attempt(item_state: dict[str, Any], stage: str, result: dict[str, Any], extra: dict[str, Any] | None = None) -> None:
    record = summarize_result(result)
    record["stage"] = stage
    if extra:
        record.update(extra)
    item_state.setdefault("attempts", []).append(record)
    item_state["last_stage"] = stage


def stage_history(item_state: dict[str, Any], message: str, **extra: Any) -> None:
    entry = {"at": utc_now(), "message": message}
    if extra:
        entry.update(extra)
    item_state.setdefault("history", []).append(entry)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sequential, resumable RSS autopublish orchestrator for pi-blog-demo.")
    parser.add_argument("--bundle-script", default=str(DEFAULT_BUNDLE_SCRIPT))
    parser.add_argument("--bundle-file", help="Use a saved bundle JSON instead of invoking the live bundle script.")
    parser.add_argument("--state-script", default=str(DEFAULT_STATE_SCRIPT))
    parser.add_argument("--build-spec-script", default=str(DEFAULT_BUILD_SPEC))
    parser.add_argument("--build-detail-script", default=str(DEFAULT_BUILD_DETAIL))
    parser.add_argument("--refine-detail-script", default=str(DEFAULT_REFINE_DETAIL))
    parser.add_argument("--upsert-script", default=str(DEFAULT_UPSERT))
    parser.add_argument("--validate-script", default=str(DEFAULT_VALIDATE))
    parser.add_argument("--articles", default=str(DEFAULT_ARTICLES))
    parser.add_argument("--source-cache-dir", default=str(DEFAULT_SOURCE_CACHE))
    parser.add_argument("--spec-dir", default=str(DEFAULT_SPEC_DIR))
    parser.add_argument("--detail-dir", default=str(DEFAULT_DETAIL_DIR))
    parser.add_argument("--article-id", action="append", dest="article_ids", type=int, help="Only process selected RSS article id(s). Repeatable.")
    parser.add_argument("--max-items", type=int, default=0, help="Process at most N new items; 0 means all.")
    parser.add_argument("--pi-timeout", type=int, default=420)
    parser.add_argument("--pi-limit", type=int, default=4, help="Refine at most N blocks per invocation (0 means all).")
    parser.add_argument("--scan-timeout", type=int, default=300)
    parser.add_argument("--html-timeout", type=int, default=120)
    parser.add_argument("--detail-timeout", type=int, default=120)
    parser.add_argument("--upsert-timeout", type=int, default=120)
    parser.add_argument("--validate-timeout", type=int, default=60)
    parser.add_argument("--max-item-retries", type=int, default=2)
    parser.add_argument("--allow-publish", action="store_true", help="Enable detail.available=true when Chinese detail is fully ready.")
    parser.add_argument("--git-commit", action="store_true", help="Create a local commit in pi-blog-demo when a batch succeeds.")
    parser.add_argument("--git-push", action="store_true", help="Push origin/master after a successful validated batch.")
    parser.add_argument("--strict-publish", action="store_true", help="Skip items unless detail.available=true (no draft-only inserts).")
    parser.add_argument("--resume-run", help="Resume a previous run id. Defaults to latest unfinished run.")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def determine_resume_run_id(explicit_run_id: str | None) -> str | None:
    if explicit_run_id:
        return explicit_run_id
    current = read_json(CURRENT_RUN_PATH, default=None)
    if isinstance(current, dict) and current.get("status") in {"running", "partial"}:
        return normalize_space(current.get("run_id")) or None
    latest = read_json(LATEST_RUN_PATH, default=None)
    if isinstance(latest, dict) and latest.get("status") in {"running", "partial"}:
        return normalize_space(latest.get("run_id")) or None
    return None


def init_run_record(args: argparse.Namespace, bundle: dict[str, Any], run_id: str | None = None) -> dict[str, Any]:
    run_identifier = run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    temp_root = RUNTIME_DIR / "tmp" / run_identifier if args.dry_run else None
    return {
        "run_id": run_identifier,
        "status": "running",
        "started_at": utc_now(),
        "updated_at": utc_now(),
        "bundle_generated_at": bundle.get("generated_at"),
        "bundle_max_new_id": bundle.get("max_new_id"),
        "last_seen_article_id": bundle.get("last_seen_article_id"),
        "articles_path": str(Path(args.articles).resolve()),
        "dry_run_temp_root": str(temp_root.resolve()) if temp_root else None,
        "items": [],
        "batch_summary": {
            "new_count": int(bundle.get("new_count") or 0),
            "terminal_count": 0,
            "published": 0,
            "draft_only": 0,
            "blocked": 0,
            "failed": 0,
            "skipped_existing": 0,
        },
        "notes": [],
    }


def bundle_items(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    items = bundle.get("items")
    if isinstance(items, list) and items:
        return [item for item in items if isinstance(item, dict)]
    merged = []
    for key in ("focus_items", "other_items"):
        for item in bundle.get(key) or []:
            if isinstance(item, dict):
                merged.append(item)
    seen = set()
    result = []
    for item in merged:
        key = (item.get("id"), item.get("url"))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def build_bundle(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    if args.bundle_file:
        bundle_path = Path(args.bundle_file).resolve()
        payload = read_json(bundle_path, default={})
        if not isinstance(payload, dict):
            raise RuntimeError(f"saved bundle is not a JSON object: {bundle_path}")
        result = {
            "ok": True,
            "code": 0,
            "stdout": json.dumps(payload, ensure_ascii=False, indent=2),
            "stderr": "",
            "started_at": utc_now(),
            "finished_at": utc_now(),
            "cmd": ["saved-bundle", str(bundle_path)],
        }
        return payload, result

    result = run_command(
        ["python3", args.bundle_script, "--state-limit", "0", "--pretty"],
        cwd=WORKSPACE,
        timeout=args.scan_timeout,
        heartbeat_seconds=30,
    )
    payload, error = parse_json_stdout(result)
    if error or not isinstance(payload, dict):
        raise RuntimeError(f"failed to parse bundle output: {error}\n{result.get('stdout','')[:2000]}")
    return payload, result


def git_has_changes(repo: Path) -> bool:
    result = run_command(["git", "status", "--porcelain"], cwd=repo, timeout=30)
    return bool(normalize_space(result.get("stdout")))


def maybe_git_commit_and_push(args: argparse.Namespace, run_record: dict[str, Any]) -> dict[str, Any]:
    outcome = {"commit": None, "push": None}
    if not args.git_commit and not args.git_push:
        return outcome
    if not git_has_changes(SITE_ROOT):
        outcome["note"] = "no_changes"
        return outcome

    allowed_outcomes = COMMITTABLE_OUTCOMES
    item_outcomes = [item.get("outcome") for item in (run_record.get("items") or [])]
    if allowed_outcomes is not None and not any(outcome in allowed_outcomes for outcome in item_outcomes):
        outcome["note"] = "commit_blocked_no_publishable_items"
        return outcome

    if args.git_commit:
        commit_message = f"Harden RSS autopublish run {run_record['run_id']}"
        add_result = run_command(
            ["git", "add", "articles.json", "assets", "source-cache", "tools/generated-specs", "tools/generated-details", "tools"],
            cwd=SITE_ROOT,
            timeout=120,
            heartbeat_seconds=30,
        )
        commit_result = run_command(
            ["git", "commit", "-m", commit_message],
            cwd=SITE_ROOT,
            timeout=120,
            heartbeat_seconds=30,
        )
        outcome["commit"] = {"add": summarize_result(add_result), "commit": summarize_result(commit_result)}
        if not commit_result.get("ok"):
            return outcome
    if args.git_push:
        push_result = run_command(
            ["git", "push", "origin", "master"],
            cwd=SITE_ROOT,
            timeout=180,
            heartbeat_seconds=30,
        )
        outcome["push"] = summarize_result(push_result)
    return outcome


def validate_publish(args: argparse.Namespace) -> dict[str, Any]:
    result = run_command(
        ["python3", args.validate_script, "--articles", args.articles, "--pretty"],
        cwd=SITE_ROOT,
        timeout=args.validate_timeout,
        heartbeat_seconds=30,
    )
    payload, _ = parse_json_stdout(result)
    return {
        "command": summarize_result(result),
        "payload": payload if isinstance(payload, dict) else None,
    }


def commit_checkpoint(args: argparse.Namespace, through_id: int) -> dict[str, Any]:
    result = run_command(
        ["python3", args.state_script, "commit", "--through-id", str(through_id)],
        cwd=WORKSPACE,
        timeout=60,
        heartbeat_seconds=30,
    )
    payload, _ = parse_json_stdout(result)
    return {
        "command": summarize_result(result),
        "payload": payload if isinstance(payload, dict) else None,
    }


def infer_item_outcome_from_spec(spec: dict[str, Any], article_post: dict[str, Any] | None) -> tuple[str, list[str]]:
    reasons: list[str] = []
    workflow = spec.get("workflow") if isinstance(spec.get("workflow"), dict) else {}
    detail = spec.get("detail") if isinstance(spec.get("detail"), dict) else {}
    progress = detail_progress(detail)

    if workflow.get("blockedBy") == "challenge":
        reasons.append("challenge_page_detected")
        return "blocked", reasons

    if article_post:
        article_detail = article_post.get("detail") if isinstance(article_post.get("detail"), dict) else {}
        article_progress = detail_progress(article_detail)
        if article_detail.get("available") and article_progress["textual_total"] > 0 and article_progress["textual_cjk"] >= article_progress["textual_total"]:
            reasons.append("detail_publishable")
            return "published", reasons
        if article_progress["block_count"] > 0:
            reasons.append("detail_draft_preserved")
            return "draft_only", reasons

    if detail.get("available"):
        reasons.append("spec_detail_available")
        return "published", reasons
    if progress["block_count"] > 0:
        reasons.append("detail_blocks_present")
        return "draft_only", reasons
    reasons.append("summary_only")
    return "draft_only", reasons


def process_item(args: argparse.Namespace, run_record: dict[str, Any], bundle: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    temp_root = Path(run_record["dry_run_temp_root"]).resolve() if run_record.get("dry_run_temp_root") else None
    effective_articles = Path(args.articles).resolve()
    effective_cache_dir = Path(args.source_cache_dir).resolve()
    effective_spec_dir = Path(args.spec_dir).resolve()
    effective_detail_dir = Path(args.detail_dir).resolve()

    if temp_root is not None:
        ensure_dir(temp_root)
        effective_articles = temp_root / "articles.json"
        effective_cache_dir = temp_root / "source-cache"
        effective_spec_dir = temp_root / "generated-specs"
        effective_detail_dir = temp_root / "generated-details"
        if not effective_articles.exists():
            effective_articles.write_text(Path(args.articles).resolve().read_text(encoding="utf-8"), encoding="utf-8")

    article_id = int(item.get("id"))
    article_title = normalize_space(item.get("title"))
    item_state = load_item_state(article_id)
    item_state.setdefault("rss_item", item)
    item_state.setdefault("run_ids", [])
    if run_record["run_id"] not in item_state["run_ids"]:
        item_state["run_ids"].append(run_record["run_id"])

    stage_history(item_state, "start_item", title=article_title, url=item.get("url"))

    build_spec_result = run_command(
        [
            "python3",
            args.build_spec_script,
            "--bundle",
            "-",
            "--id",
            str(article_id),
            "--out-dir",
            str(effective_spec_dir),
            "--cache-dir",
            str(effective_cache_dir),
            "--cache-metadata",
            "--cache-html",
        ],
        cwd=SITE_ROOT,
        timeout=args.html_timeout,
        input_text=json.dumps(bundle, ensure_ascii=False),
        heartbeat_seconds=30,
    )
    stage_attempt(item_state, "build_spec", build_spec_result)
    if not build_spec_result.get("ok"):
        item_state["outcome"] = "failed"
        item_state["terminal"] = True
        item_state["last_error"] = "build_spec_failed"
        stage_history(item_state, "build_spec_failed")
        save_item_state(article_id, item_state)
        return item_state

    build_spec_payload, parse_error = parse_json_stdout(build_spec_result)
    if parse_error or not isinstance(build_spec_payload, dict):
        item_state["outcome"] = "failed"
        item_state["terminal"] = True
        item_state["last_error"] = f"build_spec_parse_failed:{parse_error}"
        stage_history(item_state, "build_spec_parse_failed", detail=parse_error)
        save_item_state(article_id, item_state)
        return item_state

    generated = build_spec_payload.get("generated") or []
    if not generated:
        item_state["outcome"] = "failed"
        item_state["terminal"] = True
        item_state["last_error"] = "no_generated_spec"
        stage_history(item_state, "no_generated_spec")
        save_item_state(article_id, item_state)
        return item_state

    spec_path = Path(generated[0]["spec"]).resolve()
    slug_hint = normalize_space(generated[0].get("slug"))
    item_state["slug"] = slug_hint
    item_state["spec_path"] = str(spec_path)

    spec_payload = read_json(spec_path, default={})
    workflow = spec_payload.get("workflow") if isinstance(spec_payload.get("workflow"), dict) else {}
    if workflow.get("blockedBy") == "challenge":
        item_state["challenge_blocked"] = True
        stage_history(item_state, "challenge_detected", probe_title=workflow.get("probeTitle"))

    build_detail_result = run_command(
        [
            "python3",
            args.build_detail_script,
            "--spec",
            str(spec_path),
            "--source-cache-dir",
            str(effective_cache_dir),
            "--output-dir",
            str(effective_detail_dir),
            "--write-spec",
        ],
        cwd=SITE_ROOT,
        timeout=args.detail_timeout,
        heartbeat_seconds=30,
    )
    stage_attempt(item_state, "build_detail", build_detail_result)
    if build_detail_result.get("ok"):
        payload, _ = parse_json_stdout(build_detail_result)
        if isinstance(payload, dict) and payload.get("output"):
            item_state["detail_path"] = str(Path(payload["output"]).resolve())
    else:
        stage_history(item_state, "build_detail_failed")

    spec_payload = read_json(spec_path, default={})
    detail_payload = spec_payload.get("detail") if isinstance(spec_payload.get("detail"), dict) else {}
    existing_progress = detail_progress(detail_payload)
    item_state["detail_progress_before_refine"] = existing_progress

    challenge_blocked = bool(workflow.get("blockedBy") == "challenge")
    should_refine = not challenge_blocked and existing_progress["block_count"] > 0 and existing_progress["textual_total"] > existing_progress["textual_cjk"]
    if should_refine:
        refine_cmd = [
            "python3",
            args.refine_detail_script,
            "--spec",
            str(spec_path),
            "--write-spec",
            "--resume-untranslated",
            "--continue-on-error",
            "--checkpoint-every",
            "1",
            "--timeout-seconds",
            str(args.pi_timeout),
        ]
        if int(args.pi_limit or 0) > 0:
            refine_cmd.extend(["--limit", str(args.pi_limit)])
        if args.allow_publish:
            refine_cmd.append("--enable-detail")
        refine_result = run_command(
            refine_cmd,
            cwd=SITE_ROOT,
            timeout=max(args.pi_timeout + 30, args.pi_timeout * 2),
            heartbeat_seconds=30,
        )
        stage_attempt(item_state, "refine_detail", refine_result)
        if refine_result.get("ok"):
            payload, _ = parse_json_stdout(refine_result)
            if isinstance(payload, dict) and payload.get("output"):
                item_state["zh_detail_path"] = str(Path(payload["output"]).resolve())
            stage_history(item_state, "refine_detail_finished")
            spec_payload = read_json(spec_path, default={})
        else:
            stage_history(item_state, "refine_detail_failed", timeout=bool(refine_result.get("timeout")))
            if refine_result.get("timeout"):
                item_state["soft_fail"] = "refine_timeout"
    else:
        stage_history(item_state, "refine_skipped", challenge_blocked=challenge_blocked, detail_progress=existing_progress)

    # Optional strict publish: only insert when detail is publishable
    if args.strict_publish:
        spec_for_publish = read_json(spec_path, default={})
        detail_for_publish = spec_for_publish.get("detail") if isinstance(spec_for_publish.get("detail"), dict) else {}
        progress = detail_progress(detail_for_publish)
        should_skip = (
            (not detail_for_publish.get("available"))
            or (progress["block_count"] == 0)
            or (progress["textual_total"] > 0 and progress["textual_cjk"] < progress["textual_total"])
        )
        if should_skip:
            item_state["outcome"] = "blocked" if challenge_blocked else "draft_only"
            item_state["terminal"] = True
            item_state["reasons"] = ["strict_publish_skipped"]
            stage_history(item_state, "strict_publish_skipped", detail_progress=progress)
            save_item_state(article_id, item_state)
            return item_state

    upsert_result = run_command(
        [
            "python3",
            args.upsert_script,
            "--spec",
            str(spec_path),
            "--articles",
            str(effective_articles),
        ],
        cwd=SITE_ROOT,
        timeout=args.upsert_timeout,
        heartbeat_seconds=30,
    )
    stage_attempt(item_state, "upsert", upsert_result)
    if not upsert_result.get("ok"):
        item_state["outcome"] = "failed"
        item_state["terminal"] = True
        item_state["last_error"] = "upsert_failed"
        stage_history(item_state, "upsert_failed")
        save_item_state(article_id, item_state)
        return item_state

    articles_payload = load_articles_payload(effective_articles)
    article_post = find_existing_post(
        articles_payload.get("posts") or [],
        slug=slug_hint or spec_payload.get("slug"),
        url=spec_payload.get("url"),
        title=spec_payload.get("title"),
    )
    outcome, reasons = infer_item_outcome_from_spec(spec_payload, article_post)
    item_state["outcome"] = outcome
    item_state["terminal"] = outcome in TERMINAL_OUTCOMES
    item_state["reasons"] = reasons
    item_state["last_error"] = None if outcome != "failed" else item_state.get("last_error")
    item_state["post_snapshot"] = {
        "slug": article_post.get("slug") if isinstance(article_post, dict) else spec_payload.get("slug"),
        "title": article_post.get("title") if isinstance(article_post, dict) else spec_payload.get("title"),
        "detail": detail_progress((article_post or {}).get("detail") if isinstance(article_post, dict) else spec_payload.get("detail")),
        "detail_available": bool(((article_post or {}).get("detail") or {}).get("available")) if isinstance(article_post, dict) else bool((spec_payload.get("detail") or {}).get("available")),
        "articles_path": str(effective_articles),
    }
    stage_history(item_state, "item_terminal", outcome=outcome, reasons=reasons)
    save_item_state(article_id, item_state)
    return item_state


def update_run_record(run_record: dict[str, Any], item_state: dict[str, Any]) -> None:
    article_id = int(item_state["article_id"])
    found = False
    for idx, item in enumerate(run_record.get("items") or []):
        if int(item.get("article_id") or -1) == article_id:
            run_record["items"][idx] = {
                "article_id": article_id,
                "title": item_state.get("rss_item", {}).get("title"),
                "slug": item_state.get("slug"),
                "outcome": item_state.get("outcome"),
                "terminal": bool(item_state.get("terminal")),
                "updated_at": item_state.get("updated_at"),
            }
            found = True
            break
    if not found:
        run_record.setdefault("items", []).append({
            "article_id": article_id,
            "title": item_state.get("rss_item", {}).get("title"),
            "slug": item_state.get("slug"),
            "outcome": item_state.get("outcome"),
            "terminal": bool(item_state.get("terminal")),
            "updated_at": item_state.get("updated_at"),
        })

    summary = {
        "new_count": run_record.get("batch_summary", {}).get("new_count", 0),
        "terminal_count": 0,
        "published": 0,
        "draft_only": 0,
        "blocked": 0,
        "failed": 0,
        "skipped_existing": 0,
    }
    for item in run_record.get("items") or []:
        outcome = item.get("outcome")
        if item.get("terminal"):
            summary["terminal_count"] += 1
        if outcome in summary:
            summary[outcome] += 1
    run_record["batch_summary"] = summary
    run_record["updated_at"] = utc_now()


def finalize_run(args: argparse.Namespace, run_record: dict[str, Any], *, all_terminal: bool, checkpoint_through_id: int | None) -> dict[str, Any]:
    if args.dry_run:
        run_record.setdefault("notes", []).append("dry_run_no_validation_no_checkpoint")
        run_record["status"] = "ok"
        run_record["finished_at"] = utc_now()
        return run_record

    validation = validate_publish(args)
    run_record["validation"] = validation

    if not validation.get("payload", {}).get("ok"):
        run_record["status"] = "partial"
        run_record.setdefault("notes", []).append("publish_validation_failed")
        run_record["finished_at"] = utc_now()
        return run_record

    if all_terminal and checkpoint_through_id is not None:
        checkpoint = commit_checkpoint(args, checkpoint_through_id)
        run_record["checkpoint_commit"] = checkpoint
        if not checkpoint.get("command", {}).get("ok"):
            run_record["status"] = "partial"
            run_record.setdefault("notes", []).append("checkpoint_commit_failed")
            run_record["finished_at"] = utc_now()
            return run_record
    else:
        run_record.setdefault("notes", []).append("checkpoint_not_committed")
        run_record["status"] = "partial"
        run_record["finished_at"] = utc_now()
        return run_record

    git_outcome = maybe_git_commit_and_push(args, run_record)
    run_record["git"] = git_outcome
    push_ok = True
    if args.git_push and isinstance(git_outcome.get("push"), dict):
        push_ok = bool(git_outcome["push"].get("ok"))
    run_record["status"] = "ok" if push_ok else "partial"
    if not push_ok:
        run_record.setdefault("notes", []).append("git_push_failed")
    run_record["finished_at"] = utc_now()
    return run_record


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    ensure_dir(RUNTIME_DIR)
    ensure_dir(RUNS_DIR)
    ensure_dir(ITEMS_DIR)

    resume_run_id = determine_resume_run_id(args.resume_run)
    bundle, bundle_result = build_bundle(args)
    items = bundle_items(bundle)
    if args.article_ids:
        allowed_ids = {int(value) for value in args.article_ids}
        items = [item for item in items if int(item.get("id") or 0) in allowed_ids]
    if int(args.max_items or 0) > 0:
        items = items[: int(args.max_items)]

    run_record = init_run_record(args, bundle, run_id=resume_run_id)
    run_record["bundle_command"] = summarize_result(bundle_result, stdout_lines=120, stderr_lines=40)
    run_record["items_planned"] = len(items)

    run_path = RUNS_DIR / f"{run_record['run_id']}.json"
    write_json(run_path, run_record)
    write_json(CURRENT_RUN_PATH, run_record)
    write_json(LATEST_RUN_PATH, run_record)

    fatal_error = None
    try:
        for item in items:
            article_id = int(item.get("id"))
            item_state = load_item_state(article_id)
            item_state.setdefault("rss_item", item)
            item_state.setdefault("run_ids", [])
            if run_record["run_id"] not in item_state["run_ids"]:
                item_state["run_ids"].append(run_record["run_id"])
            # Always process items even if a prior terminal outcome exists (no "already processed" skipping).

            item_state = process_item(args, run_record, bundle, item)
            while item_state.get("outcome") == "failed" and int(item_state.get("retry_count") or 0) < max(0, int(args.max_item_retries or 0)):
                item_state["retry_count"] = int(item_state.get("retry_count") or 0) + 1
                stage_history(item_state, "retry_item", retry_count=item_state["retry_count"])
                save_item_state(article_id, item_state)
                item_state = process_item(args, run_record, bundle, item)

            update_run_record(run_record, item_state)
            write_json(run_path, run_record)
            write_json(CURRENT_RUN_PATH, run_record)
            write_json(LATEST_RUN_PATH, run_record)
    except Exception as exc:
        fatal_error = {
            "message": str(exc),
            "traceback": traceback.format_exc(),
        }

    all_terminal = all(bool(item.get("terminal")) for item in (run_record.get("items") or [])) and len(run_record.get("items") or []) == len(items)
    all_committable = all((item.get("outcome") in COMMITTABLE_OUTCOMES) for item in (run_record.get("items") or [])) and len(run_record.get("items") or []) == len(items)
    if fatal_error:
        run_record["status"] = "partial"
        run_record["fatal_error"] = fatal_error
        run_record.setdefault("notes", []).append("fatal_error")
        run_record["finished_at"] = utc_now()
    else:
        checkpoint_through_id = int(bundle.get("max_new_id") or 0) if items else int(bundle.get("last_seen_article_id") or 0)
        run_record = finalize_run(args, run_record, all_terminal=(all_terminal and all_committable), checkpoint_through_id=checkpoint_through_id)
        if all_terminal and not all_committable:
            run_record.setdefault("notes", []).append("terminal_but_not_committable")

    write_json(run_path, run_record)
    write_json(LATEST_RUN_PATH, run_record)
    if run_record.get("status") == "ok":
        final_current = deepcopy(run_record)
        final_current["status"] = "idle"
        write_json(CURRENT_RUN_PATH, final_current)
    else:
        write_json(CURRENT_RUN_PATH, run_record)

    print(json.dumps(run_record, ensure_ascii=False, indent=2))
    return 0 if run_record.get("status") == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
