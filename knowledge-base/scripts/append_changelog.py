"""
append_changelog.py — Append a new entry to knowledge-base/CHANGELOG.md.

Usage:
    python scripts/append_changelog.py --summary "One-line section title" \
        --added "1-projects/foo.md: why it was added" \
        --added "3-resources/concepts/bar.md: another new doc" \
        --updated "3-resources/concepts/glossary.md: added 5 new acronyms"

The script groups entries under today's date. If today already has a block, a new
section is appended under it with the summary as the heading.

Exit codes:
    0 — success
    1 — write error
"""

import argparse
import re
import sys
from datetime import date
from pathlib import Path


def render_section(summary: str, added: list, updated: list, removed: list) -> list[str]:
    lines = [f"### {summary}"]
    if added:
        for item in added:
            lines.append(f"- **Added** {item}")
    if updated:
        for item in updated:
            lines.append(f"- **Updated** {item}")
    if removed:
        for item in removed:
            lines.append(f"- **Removed** {item}")
    lines.append("")
    return lines


def main():
    parser = argparse.ArgumentParser(description="Append an entry to CHANGELOG.md")
    parser.add_argument("--summary", required=True, help="Section heading (1 line)")
    parser.add_argument("--added", action="append", default=[], help="Added item (can repeat)")
    parser.add_argument("--updated", action="append", default=[], help="Updated item (can repeat)")
    parser.add_argument("--removed", action="append", default=[], help="Removed item (can repeat)")
    parser.add_argument("--path", default=None, help="Path to CHANGELOG.md (default: knowledge-base/CHANGELOG.md)")
    args = parser.parse_args()

    if not (args.added or args.updated or args.removed):
        print("Error: at least one --added / --updated / --removed entry is required.", file=sys.stderr)
        sys.exit(1)

    kb_root = Path(__file__).resolve().parent.parent
    changelog = Path(args.path) if args.path else kb_root / "CHANGELOG.md"

    today = date.today().isoformat()
    today_header = f"## {today}"

    if not changelog.exists():
        # Create fresh
        header_block = [
            "# Knowledge Base Changelog",
            "",
            "Rolling log of KB additions and updates. Newest entries on top.",
            "",
            "---",
            "",
            today_header,
            "",
        ]
        section = render_section(args.summary, args.added, args.updated, args.removed)
        changelog.write_text("\n".join(header_block + section), encoding="utf-8")
        print(f"Created {changelog} with new entry under {today}.")
        sys.exit(0)

    existing = changelog.read_text(encoding="utf-8").splitlines()
    # Find today's date block (if exists) — insert new section right under it.
    today_idx = None
    for i, line in enumerate(existing):
        if line.strip() == today_header:
            today_idx = i
            break

    section = render_section(args.summary, args.added, args.updated, args.removed)

    if today_idx is not None:
        # insert new section after today_header (preserve blank line)
        insert_at = today_idx + 1
        # Skip blank line if present
        if insert_at < len(existing) and existing[insert_at].strip() == "":
            insert_at += 1
        new_lines = existing[:insert_at] + section + existing[insert_at:]
    else:
        # insert a new date block right after the `---` separator (or end if none)
        sep_idx = None
        for i, line in enumerate(existing):
            if line.strip() == "---":
                sep_idx = i
                break
        insert_at = (sep_idx + 2) if sep_idx is not None else len(existing)
        block = [today_header, ""] + section
        new_lines = existing[:insert_at] + block + existing[insert_at:]

    try:
        changelog.write_text("\n".join(new_lines) + ("\n" if not new_lines[-1].endswith("\n") else ""), encoding="utf-8")
    except Exception as exc:
        print(f"Error writing {changelog}: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Appended {1 + len(args.added) + len(args.updated) + len(args.removed)} item(s) to {changelog} under {today}.")


if __name__ == "__main__":
    main()
