from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
sys.path.insert(0, str(TOOLS))

from rss_workflow_utils import (  # noqa: E402
    choose_preferred_title,
    classify_web_content,
    detail_progress,
    is_detail_publishable,
    pick_richer_detail,
    slugify,
)


def test_choose_preferred_title_rejects_challenge_probe():
    assert choose_preferred_title("Real article title", "Just a moment...") == "Real article title"


def test_classify_web_content_detects_cloudflare_marker():
    assert classify_web_content(title="Anything", text="Checking if the site connection is secure via Cloudflare") == "challenge"


def test_slugify_keeps_original_article_title():
    assert slugify("Lenovo Slim 7i Aura Edition is an lightweight laptop with Intel Panther Lake") == "lenovo-slim-7i-aura-edition-is-an-lightweight-laptop-with-intel-panther-lake"


def test_detail_publishable_requires_cjk_textual_blocks():
    draft = {
        "available": False,
        "blocks": [
            {"type": "paragraph", "html": "English only paragraph."},
            {"type": "heading", "level": 2, "text": "Section"},
        ],
    }
    assert detail_progress(draft) == {"block_count": 2, "textual_total": 2, "textual_cjk": 0}
    assert not is_detail_publishable(draft)

    zh = {
        "available": True,
        "blocks": [
            {"type": "paragraph", "html": "中文段落。"},
            {"type": "heading", "level": 2, "text": "小节"},
        ],
    }
    assert is_detail_publishable(zh)


def test_pick_richer_detail_preserves_existing_publishable_detail():
    existing = {
        "available": True,
        "blocks": [
            {"type": "paragraph", "html": "中文段落。"},
            {"type": "heading", "level": 2, "text": "小节"},
        ],
    }
    incoming = {
        "available": False,
        "blocks": [
            {"type": "paragraph", "html": "Current auto-fetch only hit a challenge page."},
        ],
    }
    chosen = pick_richer_detail(existing, incoming)
    assert chosen["available"] is True
    assert len(chosen["blocks"]) == 2
