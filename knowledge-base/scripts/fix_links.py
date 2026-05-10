"""
fix_links.py — Normalize internal markdown links to the KB convention.

Rules applied (matches CLAUDE.md "Link Convention"):
  1. Every internal .md link must use a relative path with './' or '../' prefix.
  2. Bare filenames (e.g., 'foo.md') in same directory get rewritten to './foo.md'.
  3. kb-root-style paths (e.g., '2-areas/systems/foo.md' from a deep file) get
     rewritten to the proper relative form when the target exists at kb_root/<path>.
  4. Targets that don't resolve under either interpretation are left alone and
     reported as still-broken.

Usage:
    python scripts/fix_links.py             # dry-run (show planned changes)
    python scripts/fix_links.py --apply     # write changes to files

Exit codes:
    0 — done (dry-run prints planned changes; apply writes them).
    2 — unexpected error.
"""

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Iterator, Optional

LINK_RE = re.compile(r'(?<!\!)\[([^\]]+)\]\(([^)]+)\)')

SKIP_DIRS = {"_archive", "4-archives", "node_modules", ".venv", "templates"}


def iter_md_files(kb_root: Path) -> Iterator[Path]:
    for p in kb_root.rglob("*.md"):
        rel = p.relative_to(kb_root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        yield p


def is_external(target: str) -> bool:
    lowered = target.lower()
    return lowered.startswith(("http://", "https://", "mailto:", "ftp://", "tel:"))


def split_anchor(target: str) -> tuple[str, str]:
    if "#" in target:
        path_part, anchor = target.split("#", 1)
        return path_part, "#" + anchor
    return target, ""


def relpath_posix(target_abs: Path, source_dir: Path) -> str:
    rel = os.path.relpath(target_abs, start=source_dir)
    rel = rel.replace(os.sep, "/")
    if not rel.startswith(("./", "../")):
        rel = "./" + rel
    return rel


def build_basename_index(kb_root: Path) -> dict[str, list[Path]]:
    """Map filename → list of absolute paths for unique-basename resolution."""
    idx: dict[str, list[Path]] = {}
    for p in iter_md_files(kb_root):
        idx.setdefault(p.name, []).append(p.resolve())
    return idx


def rewrite_target(
    target: str,
    source_file: Path,
    kb_root: Path,
    basename_index: dict[str, list[Path]],
) -> Optional[str]:
    """Return a rewritten target string, or None if no change needed/possible."""
    if not target or is_external(target) or target.startswith("#"):
        return None

    path_part, anchor = split_anchor(target)
    if not path_part.endswith(".md"):
        return None  # only normalize .md links; leave other refs untouched
    if "..." in path_part:
        return None  # template placeholder

    # Normalize backslashes → forward slashes (Windows-generated paths break
    # GitHub render and POSIX file:// links). Force a rewrite if any were present.
    had_backslash = "\\" in path_part
    if had_backslash:
        path_part = path_part.replace("\\", "/")

    source_dir = source_file.parent

    # Already starts with ./ or ../ — only fix if file doesn't exist (or backslash forced rewrite)
    if path_part.startswith("./") or path_part.startswith("../"):
        candidate = (source_dir / path_part).resolve()
        if candidate.exists():
            return path_part + anchor if had_backslash else None
        # Broken relative — try kb-root reinterpretation
        kb_candidate = (kb_root / path_part.lstrip("./").lstrip("../")).resolve()
        if kb_candidate.exists():
            return relpath_posix(kb_candidate, source_dir) + anchor
        # Fall back to unique-basename
        basename = Path(path_part).name
        matches = basename_index.get(basename, [])
        if len(matches) == 1:
            return relpath_posix(matches[0], source_dir) + anchor
        return None

    if path_part.startswith("/"):
        return None  # absolute — leave for human review

    # No prefix → could be (a) sibling, (b) kb-root-style, (c) unique-basename, (d) plain-broken
    sibling_candidate = (source_dir / path_part).resolve()
    if sibling_candidate.exists():
        return relpath_posix(sibling_candidate, source_dir) + anchor

    kb_candidate = (kb_root / path_part).resolve()
    if kb_candidate.exists():
        return relpath_posix(kb_candidate, source_dir) + anchor

    # Unique-basename fallback: if target is just a filename and exactly one
    # file matches across the KB, rewrite to point at it. Skip ambiguous cases.
    basename = Path(path_part).name
    if basename == path_part:
        matches = basename_index.get(basename, [])
        if len(matches) == 1:
            return relpath_posix(matches[0], source_dir) + anchor

    return None


def process_file(
    md_file: Path,
    kb_root: Path,
    basename_index: dict[str, list[Path]],
) -> tuple[str, list[tuple[int, str, str]]]:
    """Return (new_text, changes). changes = list of (line_no, old_target, new_target)."""
    text = md_file.read_text(encoding="utf-8")
    changes: list[tuple[int, str, str]] = []
    new_lines: list[str] = []
    for line_no, line in enumerate(text.splitlines(keepends=False), 1):
        def repl(m: re.Match) -> str:
            label, target = m.group(1), m.group(2).strip()
            new_target = rewrite_target(target, md_file, kb_root, basename_index)
            if new_target is None or new_target == target:
                return m.group(0)
            changes.append((line_no, target, new_target))
            return f"[{label}]({new_target})"

        new_lines.append(LINK_RE.sub(repl, line))

    new_text = "\n".join(new_lines)
    if text.endswith("\n"):
        new_text += "\n"
    return new_text, changes


def atomic_write(path: Path, content: str) -> None:
    fd, tmp = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize internal markdown links.")
    parser.add_argument("--apply", action="store_true", help="Write changes to disk (default: dry-run)")
    args = parser.parse_args()

    kb_root = Path(__file__).resolve().parent.parent
    basename_index = build_basename_index(kb_root)
    total_changes = 0
    files_touched = 0

    for md_file in iter_md_files(kb_root):
        new_text, changes = process_file(md_file, kb_root, basename_index)
        if not changes:
            continue
        files_touched += 1
        total_changes += len(changes)
        rel = md_file.relative_to(kb_root)
        print(f"{rel}  ({len(changes)} change{'s' if len(changes) != 1 else ''})")
        for line_no, old, new in changes:
            print(f"  L{line_no}: {old}  →  {new}")
        if args.apply:
            atomic_write(md_file, new_text)

    suffix = " (dry-run)" if not args.apply else " (applied)"
    print(f"\n{total_changes} change(s) across {files_touched} file(s){suffix}.")
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Error: Unexpected error: {exc}", file=sys.stderr)
        sys.exit(2)
