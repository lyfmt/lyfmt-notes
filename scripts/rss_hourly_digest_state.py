#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = os.path.expanduser("~/.blogwatcher/blogwatcher.db")
STATE_PATH = Path("/home/node/.openclaw/workspace/.openclaw/runtime/rss-hourly-state.json")


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def connect_db():
    if not os.path.exists(DB_PATH):
        raise SystemExit(json.dumps({"error": f"blogwatcher database not found at {DB_PATH}"}, ensure_ascii=False))
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_max_id(conn):
    row = conn.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM articles").fetchone()
    return int(row["max_id"] or 0)


def load_state():
    if not STATE_PATH.exists():
        return None
    with STATE_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_state(data):
    ensure_parent(STATE_PATH)
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def cmd_init(args):
    conn = connect_db()
    max_id = get_max_id(conn)
    state = {
        "version": 1,
        "last_seen_article_id": max_id,
        "initialized_at": utc_now(),
        "updated_at": utc_now(),
        "db_path": DB_PATH,
    }
    save_state(state)
    print(json.dumps({"ok": True, "state_path": str(STATE_PATH), "last_seen_article_id": max_id}, ensure_ascii=False))


def cmd_status(args):
    state = load_state()
    if state is None:
        print(json.dumps({"initialized": False, "state_path": str(STATE_PATH)}, ensure_ascii=False))
        return
    conn = connect_db()
    current_max_id = get_max_id(conn)
    print(json.dumps({
        "initialized": True,
        "state_path": str(STATE_PATH),
        "last_seen_article_id": int(state.get("last_seen_article_id", 0)),
        "current_max_article_id": current_max_id,
        "pending_count_estimate": max(0, current_max_id - int(state.get("last_seen_article_id", 0))),
        "updated_at": state.get("updated_at"),
    }, ensure_ascii=False))


def query_new(conn, last_seen_id, limit=None):
    sql = """
    SELECT a.id, a.title, a.url, a.published_date, a.discovered_date, a.is_read,
           b.name AS blog_name
    FROM articles a
    JOIN blogs b ON b.id = a.blog_id
    WHERE a.id > ?
    ORDER BY a.id ASC
    """
    params = [last_seen_id]
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    items = []
    for row in rows:
        items.append({
            "id": int(row["id"]),
            "title": row["title"],
            "blog": row["blog_name"],
            "url": row["url"],
            "published": row["published_date"],
            "discovered": row["discovered_date"],
            "is_read": bool(row["is_read"]),
        })
    return items


def cmd_new(args):
    state = load_state()
    if state is None:
        print(json.dumps({
            "error": "state_not_initialized",
            "hint": f"Run: python3 {__file__} init"
        }, ensure_ascii=False))
        sys.exit(1)
    last_seen_id = int(state.get("last_seen_article_id", 0))
    conn = connect_db()
    items = query_new(conn, last_seen_id, args.limit)
    current_max_id = get_max_id(conn)
    max_new_id = max([last_seen_id] + [item["id"] for item in items])
    print(json.dumps({
        "state_path": str(STATE_PATH),
        "last_seen_article_id": last_seen_id,
        "current_max_article_id": current_max_id,
        "new_count": len(items),
        "max_new_id": max_new_id,
        "items": items,
    }, ensure_ascii=False, indent=2))


def cmd_commit(args):
    state = load_state()
    if state is None:
        print(json.dumps({
            "error": "state_not_initialized",
            "hint": f"Run: python3 {__file__} init"
        }, ensure_ascii=False))
        sys.exit(1)
    through_id = int(args.through_id)
    current = int(state.get("last_seen_article_id", 0))
    if through_id < current:
        print(json.dumps({
            "error": "invalid_through_id",
            "current_last_seen_article_id": current,
            "through_id": through_id
        }, ensure_ascii=False))
        sys.exit(1)
    state["last_seen_article_id"] = through_id
    state["updated_at"] = utc_now()
    save_state(state)
    print(json.dumps({"ok": True, "last_seen_article_id": through_id, "state_path": str(STATE_PATH)}, ensure_ascii=False))


def cmd_preview(args):
    conn = connect_db()
    sql = """
    SELECT a.id, a.title, a.url, a.published_date, a.discovered_date, a.is_read,
           b.name AS blog_name
    FROM articles a
    JOIN blogs b ON b.id = a.blog_id
    ORDER BY a.id DESC
    LIMIT ?
    """
    rows = conn.execute(sql, [args.limit]).fetchall()
    items = []
    for row in rows:
        items.append({
            "id": int(row["id"]),
            "title": row["title"],
            "blog": row["blog_name"],
            "url": row["url"],
            "published": row["published_date"],
            "discovered": row["discovered_date"],
            "is_read": bool(row["is_read"]),
        })
    items.reverse()
    print(json.dumps({"preview_count": len(items), "items": items}, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Stateful RSS digest delta helper for blogwatcher")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")
    sub.add_parser("status")

    p_new = sub.add_parser("new")
    p_new.add_argument("--limit", type=int, default=12)

    p_commit = sub.add_parser("commit")
    p_commit.add_argument("--through-id", type=int, required=True)

    p_preview = sub.add_parser("preview")
    p_preview.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()
    if args.command == "init":
        cmd_init(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "new":
        cmd_new(args)
    elif args.command == "commit":
        cmd_commit(args)
    elif args.command == "preview":
        cmd_preview(args)


if __name__ == "__main__":
    main()
