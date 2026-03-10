from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from validate_articles import validate_articles  # noqa: E402


def write_payload(tmp_path: Path, payload: dict) -> Path:
    path = tmp_path / "articles.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def test_validate_articles_rejects_suspicious_slug_and_title(tmp_path: Path):
    payload = {
        "site": {"title": "t", "description": "d"},
        "posts": [
            {
                "slug": "just-a-moment",
                "title": "Just a moment...",
                "publishedAt": "2026-03-09",
                "source": "Example",
                "url": "https://example.com/post",
                "excerpt": "x",
                "detail": {"available": False},
            }
        ],
    }
    result = validate_articles(write_payload(tmp_path, payload))
    assert result["ok"] is False
    assert any("polluted slug" in error for error in result["errors"])


def test_validate_articles_accepts_normal_post(tmp_path: Path):
    payload = {
        "site": {"title": "t", "description": "d"},
        "posts": [
            {
                "slug": "real-post",
                "title": "Real Post",
                "publishedAt": "2026-03-09",
                "source": "Example",
                "url": "https://example.com/post",
                "excerpt": "x",
                "detail": {"available": False},
            }
        ],
    }
    result = validate_articles(write_payload(tmp_path, payload))
    assert result["ok"] is True
