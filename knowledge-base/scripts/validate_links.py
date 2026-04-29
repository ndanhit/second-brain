"""
validate_links.py — Check that all internal markdown links resolve inside the knowledge base.

Scans every *.md file under knowledge-base/ (excluding _archive/), extracts each
[text](target) where target is a relative path (not http(s)://, not anchor-only),
and verifies the file exists.

Usage:
    python scripts/validate_links.py
    python scripts/validate_links.py --fix-suggestions    # show closest matches for broken links

Exit codes:
    0 — no broken links
    1 — one or more broken links found
    2 — unexpected error
"""

import argparse
import difflib
import re
import sys
from pathlib import Path
from typing import Iterator

# Matches [text](target) — capture target. Skips images ![...](...) is still caught, we'll filter below.
LINK_RE = re.compile(r'(?<!\!)\[([^\]]+)\]\(([^)]+)\)')

# sources list entries: "  - knowledge-base/notes/x.md" or YAML list item
FM_SOURCE_RE = re.compile(r'^\s*-\s*["\']?(knowledge-base/[^"\'\s]+)["\']?\s*$')


def iter_md_files(kb_root: Path) -> Iterator[Path]:
    for p in kb_root.rglob("*.md"):
        rel = p.relative_to(kb_root)
        parts = rel.parts
        if any(part in ("_archive", "4-archives", "node_modules", ".venv") for part in parts):
            continue
        yield p


def extract_links(file_path: Path) -> list[tuple[int, str, str]]:
    """Return list of (line_no, link_text, target) for every markdown link."""
    results = []
    text = file_path.read_text(encoding="utf-8", errors="replace")
    for line_no, line in enumerate(text.splitlines(), 1):
        for m in LINK_RE.finditer(line):
            text_label, target = m.group(1), m.group(2).strip()
            results.append((line_no, text_label, target))
    return results


def extract_frontmatter_sources(file_path: Path, kb_root: Path) -> list[tuple[int, str]]:
    """Return list of (line_no, source_path) for each item in the `sources:` frontmatter list."""
    results = []
    text = file_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return results
    # Find frontmatter range
    end = None
    for i, line in enumerate(lines[1:], 1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return results
    in_sources = False
    for i, line in enumerate(lines[1:end], 2):
        stripped = line.rstrip()
        if re.match(r'^\s*sources\s*:', stripped):
            in_sources = True
            # inline list? sources: [a, b] — skip for now
            continue
        if in_sources:
            if re.match(r'^\s*-\s', stripped):
                m = FM_SOURCE_RE.match(stripped)
                if m:
                    results.append((i, m.group(1)))
            elif stripped and not stripped.startswith(" "):
                # frontmatter key at indent 0 — sources block ended
                in_sources = False
    return results


def is_external(target: str) -> bool:
    lowered = target.lower()
    return lowered.startswith(("http://", "https://", "mailto:", "ftp://", "tel:"))


def is_anchor_only(target: str) -> bool:
    return target.startswith("#")


def resolve_target(target: str, source_file: Path, kb_root: Path) -> Path:
    """Given a link target from source_file, return the absolute path it refers to."""
    # Strip #anchor suffix
    if "#" in target:
        target = target.split("#", 1)[0]
    if not target:
        return source_file  # anchor-only — already handled earlier

    target_path = Path(target.replace("\\", "/"))

    if target_path.is_absolute():
        return target_path

    # Relative — resolve against source file's directory
    candidate = (source_file.parent / target_path).resolve()
    return candidate


def main():
    parser = argparse.ArgumentParser(description="Validate internal markdown links in the knowledge base.")
    parser.add_argument("--fix-suggestions", action="store_true", help="Show closest-match suggestions for broken links")
    args = parser.parse_args()

    kb_root = Path(__file__).resolve().parent.parent
    repo_root = kb_root.parent

    all_md_abs = [p.resolve() for p in iter_md_files(kb_root)]
    all_md_set = set(str(p) for p in all_md_abs)

    # also include note files for source-path checks
    all_files_set = set(str(p.resolve()) for p in kb_root.rglob("*") if p.is_file())

    broken: list[tuple[Path, int, str, str]] = []
    checked_count = 0

    for md_file in iter_md_files(kb_root):
        # Body links
        for line_no, text_label, target in extract_links(md_file):
            if is_external(target) or is_anchor_only(target):
                continue
            checked_count += 1
            resolved = resolve_target(target, md_file, kb_root)
            if not resolved.exists():
                broken.append((md_file, line_no, target, text_label))

        # Frontmatter sources (must be kb-root-relative paths)
        for line_no, source_path in extract_frontmatter_sources(md_file, kb_root):
            checked_count += 1
            # sources are paths relative to repo root (e.g., "knowledge-base/notes/x.md")
            resolved = (repo_root / source_path).resolve()
            if not resolved.exists():
                broken.append((md_file, line_no, source_path, "[sources]"))

    # Report
    if not broken:
        print(f"OK: {checked_count} links checked, 0 broken.")
        sys.exit(0)

    print(f"FAIL: {len(broken)} broken link(s) out of {checked_count} checked:\n", file=sys.stderr)
    for md_file, line_no, target, text_label in broken:
        rel = md_file.relative_to(kb_root)
        print(f"  {rel}:{line_no}  [{text_label}]({target})", file=sys.stderr)
        if args.fix_suggestions:
            basename = Path(target.split("#")[0]).name
            candidates = [Path(p).name for p in all_md_set]
            close = difflib.get_close_matches(basename, candidates, n=3, cutoff=0.6)
            if close:
                print(f"      suggestions: {', '.join(close)}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Error: Unexpected error: {exc}", file=sys.stderr)
        sys.exit(2)
