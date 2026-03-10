from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from build_post_spec_from_bundle import build_spec  # noqa: E402


def test_build_spec_blocks_challenge_probe_and_preserves_item_slug_basis():
    item = {
        "id": 123,
        "title": "Lenovo Slim 7i Aura Edition is an lightweight laptop with Intel Panther Lake",
        "blog": "Liliputing",
        "url": "https://example.com/lenovo",
        "published": "2026-03-09T18:04:26Z",
    }
    bundle = {
        "probes": [
            {
                "url": "https://example.com/lenovo",
                "title": "Just a moment...",
                "description": None,
            }
        ]
    }
    spec = build_spec(item, bundle)
    assert spec["slug"] == "lenovo-slim-7i-aura-edition-is-an-lightweight-laptop-with-intel-panther-lake"
    assert spec["title"] == item["title"]
    assert spec["workflow"]["blockedBy"] == "challenge"
    assert spec["detail"]["available"] is False
    assert "反爬" in spec["detail"]["sourceDescription"] or "挑战页" in spec["detail"]["sourceDescription"]


def test_build_spec_uses_good_probe_title_when_available():
    item = {
        "id": 124,
        "title": "Fallback Title",
        "blog": "The New Stack",
        "url": "https://example.com/post",
        "published": "2026-03-09T19:00:51Z",
    }
    bundle = {
        "probes": [
            {
                "url": "https://example.com/post",
                "title": "Anthropic launches a multi-agent code review tool for Claude Code",
                "description": "As AI coding tools drive a surge in pull requests...",
            }
        ]
    }
    spec = build_spec(item, bundle)
    assert spec["title"] == "Anthropic launches a multi-agent code review tool for Claude Code"
    assert spec["workflow"]["articleId"] == 124
    assert spec["detail"]["available"] is False
