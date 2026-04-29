"""
Tests for knowledge-base templates (User Story 3)

Run with: pytest knowledge-base/scripts/tests/test_templates.py -v
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import frontmatter
except ImportError:
    pytest.skip("python-frontmatter not installed", allow_module_level=True)

# Templates directory
TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

REQUIRED_FRONTMATTER_KEYS = {"title", "type", "tags", "updated", "sources"}

REQUIRED_SECTIONS = {
    "system": [
        "## Responsibility",
        "## Architecture",
        "## Key Behaviors",
        "## Dependencies",
        "## Debugging",
    ],
    "architecture": [
        "## Overview",
        "## When to Use",
        "## Advantages",
        "## Tradeoffs",
    ],
    "playbook": [
        "## Problem",
        "## Investigation Steps",
        "## Resolution",
        "## Prevention",
    ],
    "project": [
        "## Goal",
        "## Status & Milestones",
        "## Related Systems & Concepts",
    ],
    "concept": [
        "## Definition",
        "## Business Context",
        "## Related Concepts & Systems",
    ],
    "team": [
        "## Responsibilities & Scope",
        "## Members & Roles",
        "## Related Projects & Systems",
    ],
}


# ---------------------------------------------------------------------------
# T028: test_templates_frontmatter
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("template_name,expected_type", [
    ("system.md", "system"),
    ("architecture.md", "architecture"),
    ("playbook.md", "playbook"),
    ("project.md", "project"),
    ("concept.md", "concept"),
    ("team.md", "team"),
])
def test_templates_frontmatter(template_name, expected_type):
    """Each template must have all required frontmatter keys and correct type value."""
    template_path = TEMPLATES_DIR / template_name
    assert template_path.exists(), f"Template not found: {template_path}"

    post = frontmatter.load(str(template_path))
    metadata = post.metadata

    missing_keys = REQUIRED_FRONTMATTER_KEYS - set(metadata.keys())
    assert not missing_keys, (
        f"{template_name} is missing frontmatter keys: {missing_keys}"
    )

    assert metadata["type"] == expected_type, (
        f"{template_name} has type={metadata['type']!r}, expected {expected_type!r}"
    )


# ---------------------------------------------------------------------------
# T029: test_templates_sections
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("template_name,doc_type", [
    ("system.md", "system"),
    ("architecture.md", "architecture"),
    ("playbook.md", "playbook"),
    ("project.md", "project"),
    ("concept.md", "concept"),
    ("team.md", "team"),
])
def test_templates_sections(template_name, doc_type):
    """Each template must contain all required section headings for its type."""
    template_path = TEMPLATES_DIR / template_name
    assert template_path.exists(), f"Template not found: {template_path}"

    post = frontmatter.load(str(template_path))
    body = post.content

    required = REQUIRED_SECTIONS[doc_type]
    missing = [section for section in required if section not in body]
    assert not missing, (
        f"{template_name} is missing sections: {missing}"
    )
