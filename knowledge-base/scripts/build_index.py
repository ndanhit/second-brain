"""
build_index.py — Generate knowledge-index.md from all structured knowledge documents.

Usage:
    python scripts/build_index.py
    python scripts/build_index.py --output path/to/index.md

Exit codes:
    0 — success (index written, even if empty)
    1 — failure (output path not writable, unexpected error)
"""

import argparse
import os
import sys
import tempfile
from datetime import date
from pathlib import Path
from typing import Optional

try:
    import frontmatter
except ImportError:
    print(
        "Error: 'python-frontmatter' is not installed. Run: pip install python-frontmatter",
        file=sys.stderr,
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# T017: read_doc_entry
# ---------------------------------------------------------------------------

def read_doc_entry(filepath: Path, index_output_dir: Path) -> Optional[dict]:
    """
    Load YAML frontmatter from a knowledge document and return a dict with:
      - title: str
      - tags: list[str]
      - type: str
      - path: str (relative to index_output_dir)

    Returns None on parse error (prints warning to stderr).
    """
    try:
        post = frontmatter.load(str(filepath))
    except Exception as exc:
        print(
            f"Warning: Could not read frontmatter from {filepath}: {exc} — skipping",
            file=sys.stderr,
        )
        return None

    title = post.get("title", "").strip()
    if not title:
        print(
            f"Warning: Missing 'title' in frontmatter of {filepath} — skipping",
            file=sys.stderr,
        )
        return None

    tags = post.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    doc_type = post.get("type", "")

    try:
        rel_path = filepath.relative_to(index_output_dir)
    except ValueError:
        # filepath is not relative to index_output_dir — use absolute
        rel_path = filepath

    return {
        "title": title,
        "tags": [str(t) for t in tags],
        "type": doc_type,
        "path": str(rel_path),
    }


# ---------------------------------------------------------------------------
# T018: scan_category
# ---------------------------------------------------------------------------

def scan_category(category_dir: Path, index_output_dir: Path) -> list:
    """
    Glob all *.md files in category_dir, load each entry via read_doc_entry,
    sort alphabetically by title, and return the list.
    """
    if not category_dir.exists():
        return []

    entries = []
    for md_file in sorted(category_dir.rglob("*.md")):
        # Skip archived / deprecated folders
        rel_parts = md_file.relative_to(category_dir).parts
        if any(part in ("_archive", "4-archives", "node_modules", ".venv") for part in rel_parts):
            continue
        # Skip README files inside subfolders (they are folder-level docs, not entries)
        if md_file.name.lower() == "readme.md" and md_file.parent != category_dir:
            continue
        entry = read_doc_entry(md_file, index_output_dir)
        if entry is not None:
            entries.append(entry)

    # Sort alphabetically by title (case-insensitive)
    entries.sort(key=lambda e: e["title"].lower())
    return entries


# ---------------------------------------------------------------------------
# T019: render_index
# ---------------------------------------------------------------------------

CATEGORY_HEADINGS = {
    "1-projects": "## Projects",
    "2-areas/systems": "## Systems",
    "2-areas/architecture": "## Architecture Patterns",
    "2-areas/teams": "## Teams & Processes",
    "3-resources/concepts": "## Concepts & Glossary",
    "3-resources/playbooks": "## Playbooks",
}


def render_index(entries_by_category: dict, generated_date: str) -> str:
    """
    Render the knowledge-index.md content as a markdown string.

    entries_by_category: {"systems": [...], "architecture": [...], "playbooks": [...]}
    Omits categories with no entries.
    """
    lines = ["# Knowledge Index", "", f"_Generated: {generated_date}_", ""]

    for category in ("1-projects", "2-areas/systems", "2-areas/architecture", "3-resources/concepts", "3-resources/playbooks", "2-areas/teams"):
        entries = entries_by_category.get(category, [])
        if not entries:
            continue

        heading = CATEGORY_HEADINGS[category]
        lines.append(heading)
        lines.append("")

        for entry in entries:
            tags_str = ", ".join(f"`{t}`" for t in entry["tags"]) if entry["tags"] else ""
            type_str = f"`{entry['type']}`" if entry["type"] else ""

            meta_parts = [p for p in [type_str, tags_str] if p]
            meta = " — " + ", ".join(meta_parts) if meta_parts else ""

            lines.append(f"- [{entry['title']}]({entry['path']}){meta}")

        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# T020: main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate knowledge-index.md from all structured knowledge documents."
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Path to write the index file (default: knowledge-index.md in knowledge-base root)",
    )
    args = parser.parse_args()

    # Determine knowledge-base root (parent of scripts/)
    kb_root = Path(__file__).parent.parent

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = kb_root / "knowledge-index.md"

    index_output_dir = output_path.parent

    # Scan all categories
    entries_by_category = {}
    counts = {}
    for category in ("1-projects", "2-areas/systems", "2-areas/architecture", "3-resources/concepts", "3-resources/playbooks", "2-areas/teams"):
        category_dir = kb_root / category
        entries = scan_category(category_dir, index_output_dir)
        entries_by_category[category] = entries
        counts[category] = len(entries)

    # Render index
    today = date.today().isoformat()
    index_content = render_index(entries_by_category, today)

    # Atomic write
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_fd, tmp_path = tempfile.mkstemp(
            dir=output_path.parent, prefix=".tmp_index_", suffix=".md"
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                f.write(index_content)
            os.replace(tmp_path, output_path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
    except Exception as exc:
        print(f"Error: Could not write index to {output_path}: {exc}", file=sys.stderr)
        sys.exit(1)

    # Print summary
    total = sum(counts.values())
    print(f"Knowledge index written to {output_path}")
    if total == 0:
        print("  No documents found.")
    else:
        for category in ("1-projects", "2-areas/systems", "2-areas/architecture", "3-resources/concepts", "3-resources/playbooks", "2-areas/teams"):
            print(f"  {category}: {counts[category]}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)
