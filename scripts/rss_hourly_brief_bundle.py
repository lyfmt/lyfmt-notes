#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKDIR = Path("/home/node/.openclaw/workspace")
BLOGWATCHER = Path("/home/node/.local/bin/blogwatcher")
STATE_SCRIPT = WORKDIR / "scripts" / "rss_hourly_digest_state.py"
PROBE_SCRIPT = WORKDIR / "scripts" / "article_metadata_probe.py"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def run_command(cmd: list[str], timeout: int, env: dict | None = None) -> dict:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(WORKDIR),
            env=merged_env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": proc.returncode == 0,
            "code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except Exception as exc:
        return {
            "ok": False,
            "code": None,
            "stdout": "",
            "stderr": repr(exc),
        }


def tail_lines(text: str, limit: int = 80) -> list[str]:
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) <= limit:
        return lines
    return lines[-limit:]


def score_item(item: dict) -> tuple[int, int]:
    title = (item.get("title") or "").lower()
    score = 0
    positive_weights = {
        " ai": 5,
        "jvm": 5,
        "performance": 5,
        "http": 4,
        "client": 3,
        "gc": 4,
        "flight recorder": 5,
        "jfr": 5,
        "devops": 4,
        "records": 2,
        "data oriented": 4,
        "javafx": 2,
        "shipping soon": 2,
        "updates": 2,
        "monitor": 4,
    }
    negative_weights = {
        "episode": -4,
        "podcast": -4,
        "newscast": -2,
    }
    for token, weight in positive_weights.items():
        if token.strip() in title:
            score += weight
    for token, weight in negative_weights.items():
        if token in title:
            score += weight
    return (score, int(item.get("id") or 0))


def choose_focus_items(items: list[dict]) -> tuple[list[dict], list[dict]]:
    if len(items) <= 5:
        return items, []
    return items[:5], items[5:]


def choose_probe_items(items: list[dict], max_items: int = 3) -> list[dict]:
    ranked = sorted(items, key=lambda item: (score_item(item)[0], score_item(item)[1]), reverse=True)
    selected: list[dict] = []
    seen_urls: set[str] = set()
    for item in ranked:
        url = item.get("url")
        if not url or url in seen_urls:
            continue
        selected.append(item)
        seen_urls.add(url)
        if len(selected) >= max_items:
            break
    return selected


def parse_json_output(result: dict) -> tuple[dict | None, str | None]:
    stdout = (result.get("stdout") or "").strip()
    if not stdout:
        return None, "empty_stdout"
    try:
        return json.loads(stdout), None
    except Exception as exc:
        return None, f"json_parse_error: {exc!r}"


def main() -> int:
    payload: dict = {
        "ok": True,
        "generated_at": utc_now(),
        "scan": {},
        "new_count": 0,
        "max_new_id": None,
        "last_seen_article_id": None,
        "current_max_article_id": None,
        "focus_items": [],
        "other_items": [],
        "probe_candidates": [],
        "probes": [],
        "warnings": [],
        "errors": [],
    }

    scan_result = run_command([str(BLOGWATCHER), "scan"], timeout=240, env={"HOME": "/home/node"})
    payload["scan"] = {
        "ok": scan_result["ok"],
        "code": scan_result["code"],
        "stdout_tail": tail_lines(scan_result.get("stdout") or "", 120),
        "stderr_tail": tail_lines(scan_result.get("stderr") or "", 40),
    }
    if not scan_result["ok"]:
        payload["ok"] = False
        payload["warnings"].append("blogwatcher_scan_nonzero")

    state_result = run_command(["python3", str(STATE_SCRIPT), "new", "--limit", "12"], timeout=60)
    if not state_result["ok"]:
        payload["ok"] = False
        payload["errors"].append({
            "stage": "state_new",
            "code": state_result["code"],
            "stderr": (state_result.get("stderr") or "").strip(),
        })
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    state_data, parse_error = parse_json_output(state_result)
    if parse_error or state_data is None:
        payload["ok"] = False
        payload["errors"].append({
            "stage": "state_new_parse",
            "detail": parse_error,
            "stdout": (state_result.get("stdout") or "")[:4000],
        })
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    items = state_data.get("items") or []
    payload["new_count"] = int(state_data.get("new_count") or 0)
    payload["max_new_id"] = state_data.get("max_new_id")
    payload["last_seen_article_id"] = state_data.get("last_seen_article_id")
    payload["current_max_article_id"] = state_data.get("current_max_article_id")

    focus_items, other_items = choose_focus_items(items)
    payload["focus_items"] = focus_items
    payload["other_items"] = other_items

    probe_candidates = choose_probe_items(focus_items or items, max_items=3)
    payload["probe_candidates"] = probe_candidates

    if probe_candidates:
        probe_cmd = ["python3", str(PROBE_SCRIPT), "--pretty"] + [item["url"] for item in probe_candidates if item.get("url")]
        probe_result = run_command(probe_cmd, timeout=90)
        probe_data, probe_parse_error = parse_json_output(probe_result)
        if probe_data is not None:
            payload["probes"] = probe_data.get("items") or []
        else:
            payload["warnings"].append("probe_parse_failed")
            payload["errors"].append({
                "stage": "probe_parse",
                "detail": probe_parse_error,
                "stdout": (probe_result.get("stdout") or "")[:4000],
                "stderr": (probe_result.get("stderr") or "")[:2000],
            })

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
