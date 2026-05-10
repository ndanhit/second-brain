# second-brain — Project Instructions for Claude

This file is loaded automatically by Claude Code when working in this repository.

## What this repo is

A local-first PARA-method knowledge base. Users drop raw notes into `knowledge-base/notes/`, then run `./brain <path>` to have an AI agent normalize them into structured, cross-linked markdown documents.

## Active Technologies

- **Python 3.9+** — all scripts are plain Python, no packaging required.
- **python-frontmatter** — YAML frontmatter read/write for markdown files.
- **claude CLI ≥ 2.1.79** — invoked via subprocess with `--json-schema` for structured output.
- **pytest** — test runner.
- **FastAPI** (optional) — local dashboard at `knowledge-base/ui/`.

## Project Structure

```text
knowledge-base/
├── knowledge-index.md       # Generated navigation (alphabetical)
├── CHANGELOG.md             # Rolling log of KB additions/updates
├── notes/                   # Raw inbound notes (kept after ingest)
│   └── _archive/YYYY-MM/    # Processed notes — skipped by build_index/validate_links
├── 0-inbox/                 # User's explicit drop zone (delete after ingest)
├── 1-projects/              # Active initiatives
├── 2-areas/
│   ├── systems/
│   ├── architecture/
│   │   └── adrs/            # Architecture Decision Records
│   └── teams/
├── 3-resources/
│   ├── concepts/            # Domain concepts & glossary
│   └── playbooks/           # Operational runbooks
├── 4-archives/              # Deprecated / completed docs
├── prompts/                 # Reusable AI prompt templates
├── templates/               # Markdown templates per doc type
├── scripts/
│   ├── normalize_notes.py   # AI normalization + auto-merge
│   ├── build_index.py       # Index generation
│   ├── validate_links.py    # Broken-link detector
│   ├── append_changelog.py  # CHANGELOG helper
│   ├── media_ingest.py      # PDF/audio → notes
│   └── tests/               # pytest suite
├── ui/                      # Optional FastAPI dashboard
└── requirements.txt

brain                        # Bash entry point
brain.ps1                    # PowerShell entry point
start                        # Bash UI launcher
start.ps1                    # PowerShell UI launcher
```

## Commands

```bash
# Install
pip install -r knowledge-base/requirements.txt

# Ingest a note (recommended)
./brain knowledge-base/notes/<file>.md

# Normalize manually (auto-merges on collision)
python3 knowledge-base/scripts/normalize_notes.py knowledge-base/notes/<file>.md

# Force overwrite (skip auto-merge)
python3 knowledge-base/scripts/normalize_notes.py knowledge-base/notes/<file>.md --overwrite

# Rebuild the index
python3 knowledge-base/scripts/build_index.py

# Validate internal markdown links
python3 knowledge-base/scripts/validate_links.py
python3 knowledge-base/scripts/validate_links.py --fix-suggestions

# Run tests
python3 -m pytest knowledge-base/scripts/tests/ -v

# Visual dashboard
./start                # then open http://localhost:8888
```

## Skills

- **`/brain-add`** — Ingest raw notes/text into the PARA-structured KB using native intelligence (no subprocess).
- **`/brain-query`** — Search the KB before answering domain questions, cite sources.

## Code Style (for changes to scripts/)

- Python 3.9+ compatible (avoid `dict | None`; use `Optional[dict]` from `typing`).
- `argparse` for CLI argument parsing.
- `pathlib.Path` for all file operations.
- Errors → `stderr`; normal output → `stdout`.
- Atomic writes via `tempfile` + `os.replace()`.
- `sys.exit(1)` on failure; `sys.exit(0)` on success.

## Document Conventions

- **One concept per file**. Split when a doc exceeds ~800 words.
- **Lowercase kebab-case filenames** — `payment-service.md`, not `PaymentService.md`.
- **Frontmatter required** — `title`, `type`, `tags`, `updated`, `sources`.
- **Sources track origins** — every doc lists the raw note(s) it was derived from. Append on merge; don't replace.
- **Cross-links** — see "Link Convention" below.
- **English** — KB documents stay in English. Raw notes can be any language; the AI translates on normalization.
- **No secrets** — content is sent to Claude during normalization. Strip tokens, credentials, PII before ingesting.

## Link Convention

Internal links between KB notes MUST follow these rules. `validate_links.py` enforces them.

1. **Use standard markdown links only** — `[text](path.md)`. No wikilinks (`[[note]]`), no absolute paths.
2. **Always relative, always prefixed**:
   - Sibling file: `[text](./sibling.md)` — `./` prefix is required, never bare `sibling.md`.
   - Cross-folder: `[text](../../2-areas/systems/foo.md)` — count `../` from current file's directory.
   - Never write kb-root-style paths like `(2-areas/systems/foo.md)` from a file deep in the tree — that resolves against the source dir, not kb-root, and breaks.
3. **Heading anchors are encouraged** for long notes (>200 lines): `[Search flow](./other-note.md#search)`.
4. **External links** (`http://`, `https://`, `mailto:`) are unrestricted.
5. **Templates** (`templates/*.md`) and **prompts** (`prompts/*.md`) may contain placeholder targets — those are excluded from validation.
6. **Forward slashes only** — never `\`. Backslashes silently break GitHub render (encoded as `%5C`) and POSIX file:// links.

Helpers:

```bash
# Verify all internal links — exits non-zero on broken or non-conventional links.
python3 knowledge-base/scripts/validate_links.py

# Auto-normalize links to the convention (./ prefix, kb-root-style fixes, backslash → /).
python3 knowledge-base/scripts/fix_links.py --apply
```

## When the user asks to add knowledge

Prefer the `/brain-add` skill flow. If unavailable, run `./brain <path>` or invoke `normalize_notes.py` directly. After any write, run `build_index.py`.

## When the user asks a domain question

Use the `/brain-query` skill. Search index → concepts → systems/areas → notes → archive, in that order. Cite the file path. If the KB doesn't have the answer, say so before giving a general-knowledge answer.
