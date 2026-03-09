#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
import sys
from html import unescape

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"


def clean_text(value: str | None) -> str | None:
    if not value:
        return None
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value or None


def find_first(patterns, text):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            return clean_text(match.group(1))
    return None


def probe_url(url: str, timeout: int, max_bytes: int) -> dict:
    headers = [
        f"Range: bytes=0-{max_bytes - 1}",
        "Accept-Encoding: identity",
        "Accept-Language: en-US,en;q=0.9",
    ]
    cmd = [
        "curl",
        "-L",
        "--silent",
        "--show-error",
        "--max-time",
        str(timeout),
        "--connect-timeout",
        str(min(timeout, 10)),
        "--speed-time",
        str(min(timeout, 15)),
        "--speed-limit",
        "1",
        "-A",
        USER_AGENT,
    ]
    for header in headers:
        cmd.extend(["-H", header])
    cmd.append(url)

    result = {
        "url": url,
        "ok": False,
        "title": None,
        "description": None,
        "fetched_bytes": 0,
        "error": None,
    }

    try:
        proc = subprocess.run(cmd, capture_output=True, check=False, timeout=timeout + 5)
    except Exception as exc:
        result["error"] = f"probe_exception: {exc!r}"
        return result

    raw = proc.stdout or b""
    text = raw.decode("utf-8", "ignore")
    result["fetched_bytes"] = len(raw)

    if proc.returncode != 0 and not text.strip():
        err = (proc.stderr or b"").decode("utf-8", "ignore").strip()
        result["error"] = err or f"curl_exit_{proc.returncode}"
        return result

    result["title"] = find_first([
        r"<meta[^>]+property=[\"']og:title[\"'][^>]+content=[\"'](.*?)[\"']",
        r"<meta[^>]+name=[\"']twitter:title[\"'][^>]+content=[\"'](.*?)[\"']",
        r"<title>(.*?)</title>",
    ], text)

    result["description"] = find_first([
        r"<meta[^>]+property=[\"']og:description[\"'][^>]+content=[\"'](.*?)[\"']",
        r"<meta[^>]+name=[\"']description[\"'][^>]+content=[\"'](.*?)[\"']",
        r"<meta[^>]+name=[\"']twitter:description[\"'][^>]+content=[\"'](.*?)[\"']",
    ], text)

    result["ok"] = bool(result["title"] or result["description"] or text.strip())
    if not result["ok"] and proc.returncode != 0:
        err = (proc.stderr or b"").decode("utf-8", "ignore").strip()
        result["error"] = err or f"curl_exit_{proc.returncode}"
    elif not result["ok"]:
        result["error"] = "empty_response"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Best-effort article metadata probe using curl range requests")
    parser.add_argument("urls", nargs="+", help="Article URLs to probe")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--max-bytes", type=int, default=12000)
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()

    items = [probe_url(url, args.timeout, args.max_bytes) for url in args.urls]
    payload = {"count": len(items), "items": items}
    if args.pretty:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
