"""
normalize_notes.py — Convert raw meeting/onboarding notes into structured knowledge documents.

Usage:
    python scripts/normalize_notes.py notes/onboarding-2026-04-07.md
    python scripts/normalize_notes.py notes/onboarding-2026-04-07.md --overwrite

Exit codes:
    0 — success (zero or more files written)
    1 — failure (file not found, Claude error, parse error, unsafe path)
"""

import argparse
import json
import os
import sys
import subprocess
import tempfile
from datetime import date
from pathlib import Path

import build_index

# ---------------------------------------------------------------------------
# T005: Constants — OUTPUT_SCHEMA and NORMALIZE_PROMPT
# ---------------------------------------------------------------------------

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "files": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        }
    },
    "required": ["files"],
}

NORMALIZE_PROMPT_TEMPLATE = """\
Convert the following engineering meeting notes into structured knowledge base documents.

Rules:
- Each document must contain a single concept
- Categorize documents strictly into: projects / systems / architecture / concepts / playbooks / teams / adrs
- Output markdown files with valid YAML frontmatter (title, type, tags, updated, sources)
- The sources array MUST include the project-relative path: `{note_path}`
- Avoid duplication — if a concept spans multiple notes, merge into one document
- Extract operational knowledge when possible
- Target 300-800 words per document
- Use today's date for the `updated` field: {today}
- CROSS-LINKING IS MANDATORY: Whenever you mention a system, architecture, project, concept, or team, you MUST add a markdown link to it using project-relative paths (e.g. `[Payment](2-areas/systems/payment-service.md)`).
- Document types & required sections:
  - project: Goal / Status & Milestones / Related Knowledge
  - system: Responsibility / Architecture / Key Behaviors / Dependencies / Debugging / Related Knowledge
  - architecture: Overview / When to Use / Advantages / Tradeoffs / Related Knowledge
  - adr: Status / Context / Decision / Consequences / Related Knowledge
  - concept: Definition / Synonyms & Aliases / Business Context / Related Knowledge
  - playbook: Problem / Investigation Steps / Resolution / Prevention / Related Knowledge
  - team: Responsibilities & Scope / Members & Roles / Related Knowledge
- File paths must follows:
  - 1-projects/<name>.md
  - 2-areas/systems/<name>.md
  - 2-areas/architecture/<name>.md
  - 2-areas/architecture/adrs/<name>.md
  - 2-areas/teams/<name>.md
  - 3-resources/concepts/<name>.md
  - 3-resources/playbooks/<name>.md
- Use lowercase kebab-case filenames.

Notes:
{notes_content}
"""

MERGE_SCHEMA = {
    "type": "object",
    "properties": {
        "merged_content": {"type": "string"}
    },
    "required": ["merged_content"]
}

MERGE_PROMPT_TEMPLATE = """\
You are an expert technical writer. Your task is to merge new meeting notes/information into an EXISTING knowledge base document.

Instructions:
1. Preserve all existing context, structure, and history from the original document. DO NOT delete existing information unless the new information explicitly deprecates it.
2. Integrate the new information seamlessly into the relevant sections. If a new section is needed, add it manually.
3. Keep the frontmatter intact. However, you MUST append `{note_path}` to the `sources` array in the YAML frontmatter. If the `sources` array does not exist, create it.
4. Update the `updated` frontmatter field to: {today}.
5. Output the ENTIRE merged markdown file contents.

# Original Document:
{existing_content}

# New Information to Merge:
{new_content}
"""

# ---------------------------------------------------------------------------
# T006: ALLOWED_CATEGORIES and validate_output_path
# ---------------------------------------------------------------------------

ALLOWED_CATEGORIES = {"1-projects", "2-areas", "3-resources", "4-archives"}


def validate_output_path(path: str) -> bool:
    """
    Return True if the path is safe and within an allowed category.

    Rejects:
    - Path traversal attempts (contains '..')
    - Absolute paths
    - Paths whose top-level directory is not in ALLOWED_CATEGORIES
    """
    if not path:
        return False
    # Reject absolute paths
    if os.path.isabs(path):
        return False
    # Reject any path traversal component
    parts = Path(path).parts
    if any(part == ".." for part in parts):
        return False
    # Must start with an allowed category
    if len(parts) < 2:
        return False
    if parts[0] not in ALLOWED_CATEGORIES:
        return False
    # Must end with .md
    if not path.endswith(".md"):
        return False
    return True


# ---------------------------------------------------------------------------
# T007: call_claude
# ---------------------------------------------------------------------------

class ClaudeError(Exception):
    pass


def _run_claude_json(prompt: str, schema: dict) -> dict:
    """
    Invoke the claude CLI with JSON schema enforcement.
    Returns the structured_output dictionary.
    Raises ClaudeError on any failure.
    """
    cmd = [
        "claude",
        "--bare",
        "-p", prompt,
        "--output-format", "json",
        "--json-schema", json.dumps(schema),
        "--no-session-persistence",
        "--dangerously-skip-permissions",
        "--max-turns", "1",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            stdin=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        raise ClaudeError(
            "Error: 'claude' CLI not found. Is Claude Code installed and on PATH?"
        )

    if result.returncode != 0:
        stderr_msg = result.stderr.strip() if result.stderr else "(no stderr)"
        raise ClaudeError(f"Error: Claude CLI returned error: {stderr_msg}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ClaudeError(f"Error: Could not parse Claude CLI JSON output: {exc}")

    if data.get("is_error"):
        subtype = data.get("subtype", "unknown")
        if subtype == "error_max_structured_output_retries":
            raise ClaudeError(
                "Error: Claude could not produce valid structured output after maximum retries"
            )
        raise ClaudeError(f"Error: Claude CLI reported an error (subtype={subtype})")

    structured = data.get("structured_output")
    if structured is None:
        raise ClaudeError(
            "Error: Claude CLI response missing 'structured_output' field"
        )

    return structured


def call_claude(prompt: str) -> list:
    """ Legacy helper for initial note generation. """
    return _run_claude_json(prompt, OUTPUT_SCHEMA).get("files", [])


# ---------------------------------------------------------------------------
# T008: write_document
# ---------------------------------------------------------------------------

def write_document(kb_root: Path, path: str, content: str, overwrite: bool, note_path_str: str) -> str:
    """
    Write content to kb_root/path atomically.

    If the file exists and overwrite=False, performs an AI merge.
    Returns "created", "overwritten", "merged", or "skipped" (failed).
    """
    target = kb_root / path
    target.parent.mkdir(parents=True, exist_ok=True)

    status = "created"

    if target.exists():
        if overwrite:
            status = "overwritten"
        else:
            print(f"File exists: {path}. Triggering AI Merge collision...")
            try:
                existing_content = target.read_text(encoding="utf-8")
                merge_prompt = MERGE_PROMPT_TEMPLATE.format(
                    note_path=note_path_str,
                    today=date.today().isoformat(),
                    existing_content=existing_content,
                    new_content=content
                )
                merged_data = _run_claude_json(merge_prompt, MERGE_SCHEMA)
                content = merged_data.get("merged_content", content)
                status = "merged"
            except Exception as e:
                print(f"Error during AI Merge for {path}: {e}", file=sys.stderr)
                return "failed_merge"

    # Atomic write via tempfile + os.replace
    tmp_fd, tmp_path = tempfile.mkstemp(
        dir=target.parent, prefix=".tmp_", suffix=".md"
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, target)
    except Exception:
        # Clean up temp file if something went wrong
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    return status


# ---------------------------------------------------------------------------
# T009: main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Normalize raw meeting notes into structured knowledge documents using Claude."
    )
    parser.add_argument(
        "notes_file",
        help="Path to the raw notes markdown file (e.g. notes/onboarding-2026-04-07.md)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files instead of merging",
    )
    args = parser.parse_args()

    notes_path = Path(args.notes_file)

    # Validate notes file exists
    if not notes_path.exists():
        print(f"Error: File not found: {args.notes_file}", file=sys.stderr)
        sys.exit(1)

    if not notes_path.is_file():
        print(f"Error: Not a file: {args.notes_file}", file=sys.stderr)
        sys.exit(1)

    # Read note content
    notes_content = notes_path.read_text(encoding="utf-8").strip()

    if not notes_content:
        print(f"No documents generated from {args.notes_file}")
        sys.exit(0)

    # Determine knowledge-base root (parent of scripts/)
    kb_root = Path(__file__).parent.parent

    # Build prompt
    today = date.today().isoformat()
    note_path_str = f"notes/{notes_path.name}"
    prompt = NORMALIZE_PROMPT_TEMPLATE.format(
        today=today,
        note_path=note_path_str,
        notes_content=notes_content,
    )

    # Call Claude
    try:
        files = call_claude(prompt)
    except ClaudeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    if not files:
        print(f"No documents generated from {args.notes_file}")
        sys.exit(0)

    # Process each file
    had_error = False
    for file_entry in files:
        path = file_entry.get("path", "")
        content = file_entry.get("content", "")

        # Validate path
        if not validate_output_path(path):
            print(
                f"Error: Unsafe or invalid path in Claude response: {repr(path)}",
                file=sys.stderr,
            )
            had_error = True
            continue

        # Write document
        try:
            status = write_document(kb_root, path, content, args.overwrite, note_path_str)
        except Exception as exc:
            print(f"Error: Could not write {path}: {exc}", file=sys.stderr)
            had_error = True
            continue

        if status == "created":
            print(f"Created: {path}")
        elif status == "merged":
            print(f"Merged: {path}")
        elif status == "overwritten":
            print(f"Overwritten: {path}")
        else:
            print(f"Skipped/Failed: {path}")

    # Automatically rebuild the index after processing notes
    print("\nRebuilding knowledge index...")
    try:
        build_index.main()
    except Exception as exc:
        print(f"Warning: Could not rebuild index: {exc}", file=sys.stderr)

    if had_error:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Error: Unexpected error: {exc}", file=sys.stderr)
        sys.exit(1)
