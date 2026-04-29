"""
Tests for build_index.py (User Story 2)

Run with: pytest knowledge-base/scripts/tests/test_build_index.py -v
"""

import sys
from pathlib import Path

import pytest

# Ensure scripts/ is on the path
sys.path.insert(0, str(Path(__file__).parent.parent))

import build_index


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_doc(path: Path, title: str, doc_type: str, tags: list = None):
    """Write a valid knowledge document with frontmatter to path."""
    tags_yaml = "\n".join(f"  - {t}" for t in (tags or []))
    tags_block = f"tags:\n{tags_yaml}" if tags else "tags: []"
    content = (
        f"---\n"
        f"title: {title}\n"
        f"type: {doc_type}\n"
        f"{tags_block}\n"
        f"updated: 2026-04-07\n"
        f"---\n\n# {title}\n\nContent here.\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# T021: test_build_index_empty_kb
# ---------------------------------------------------------------------------

def test_build_index_empty_kb(tmp_path):
    """Empty knowledge base produces a valid index with no category sections."""
    # Create empty category dirs
    (tmp_path / "1-projects").mkdir(parents=True)
    (tmp_path / "2-areas" / "systems").mkdir(parents=True)
    (tmp_path / "2-areas" / "architecture").mkdir(parents=True)
    (tmp_path / "3-resources" / "playbooks").mkdir(parents=True)

    entries_by_category = {
        "1-projects": build_index.scan_category(tmp_path / "1-projects", tmp_path),
        "2-areas/systems": build_index.scan_category(tmp_path / "2-areas" / "systems", tmp_path),
        "2-areas/architecture": build_index.scan_category(tmp_path / "2-areas" / "architecture", tmp_path),
        "3-resources/playbooks": build_index.scan_category(tmp_path / "3-resources" / "playbooks", tmp_path),
    }

    rendered = build_index.render_index(entries_by_category, "2026-04-07")

    assert "# Knowledge Index" in rendered
    assert "## Systems" not in rendered
    assert "## Architecture Patterns" not in rendered
    assert "## Playbooks" not in rendered


# ---------------------------------------------------------------------------
# T022: test_build_index_full_kb
# ---------------------------------------------------------------------------

def test_build_index_full_kb(tmp_path):
    """Index contains correct titles, relative links, and tags for all categories."""
    make_doc(tmp_path / "2-areas" / "systems" / "payment-service.md", "Payment Service", "system", ["payment", "backend"])
    make_doc(tmp_path / "2-areas" / "architecture" / "retry-pattern.md", "Retry Pattern", "architecture", ["resilience"])
    make_doc(tmp_path / "3-resources" / "playbooks" / "debug-payment.md", "Debug Payment", "playbook", ["debugging"])

    entries_by_category = {
        "2-areas/systems": build_index.scan_category(tmp_path / "2-areas" / "systems", tmp_path),
        "2-areas/architecture": build_index.scan_category(tmp_path / "2-areas" / "architecture", tmp_path),
        "3-resources/playbooks": build_index.scan_category(tmp_path / "3-resources" / "playbooks", tmp_path),
    }

    rendered = build_index.render_index(entries_by_category, "2026-04-07")

    assert "## Systems" in rendered
    assert "## Architecture Patterns" in rendered
    assert "## Playbooks" in rendered

    assert "Payment Service" in rendered
    assert "Retry Pattern" in rendered
    assert "Debug Payment" in rendered

    assert "payment-service.md" in rendered
    assert "retry-pattern.md" in rendered
    assert "debug-payment.md" in rendered

    assert "`payment`" in rendered
    assert "`resilience`" in rendered
    assert "`debugging`" in rendered


# ---------------------------------------------------------------------------
# T023: test_build_index_skips_bad_frontmatter
# ---------------------------------------------------------------------------

def test_build_index_skips_bad_frontmatter(tmp_path, capsys):
    """Files with malformed frontmatter are skipped; others are still indexed."""
    # Good file
    make_doc(tmp_path / "2-areas" / "systems" / "good-service.md", "Good Service", "system")

    # Bad file — no frontmatter delimiters, just raw text
    bad_file = tmp_path / "2-areas" / "systems" / "bad-file.md"
    bad_file.write_text("This file has no frontmatter at all.\n\nJust raw text.", encoding="utf-8")

    entries = build_index.scan_category(tmp_path / "2-areas" / "systems", tmp_path)

    captured = capsys.readouterr()
    # Only the good file should be returned
    titles = [e["title"] for e in entries]
    assert "Good Service" in titles
    # bad-file has no title so should be skipped with a warning
    assert all(t != "" for t in titles)


# ---------------------------------------------------------------------------
# T024: test_build_index_sorted_alphabetically
# ---------------------------------------------------------------------------

def test_build_index_sorted_alphabetically(tmp_path):
    """Index entries within a category are sorted alphabetically by title."""
    make_doc(tmp_path / "2-areas" / "systems" / "zebra-service.md", "Zebra Service", "system")
    make_doc(tmp_path / "2-areas" / "systems" / "alpha-service.md", "Alpha Service", "system")
    make_doc(tmp_path / "2-areas" / "systems" / "middle-service.md", "Middle Service", "system")

    entries = build_index.scan_category(tmp_path / "2-areas" / "systems", tmp_path)
    titles = [e["title"] for e in entries]

    assert titles == ["Alpha Service", "Middle Service", "Zebra Service"]
