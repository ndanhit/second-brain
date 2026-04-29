# second-brain

A local-first, AI-augmented personal knowledge base built on the [PARA method](https://fortelabs.com/blog/para/). Capture raw notes, run one command, and let an AI agent normalize them into a clean, cross-linked knowledge graph stored in plain markdown — version-controlled in Git, readable by humans and AI agents alike.

This repo is a **template**. Clone it, rename it, and start dropping notes into `knowledge-base/notes/`. No SaaS, no vector DB, no API keys to manage — authentication is handled by your local Claude Code install.

---

## Why this exists

Most note-taking tools either:
- lock your knowledge into a proprietary format (Notion, Obsidian Sync, …), or
- give you a flat folder of markdown that nobody re-reads after the meeting ends.

**second-brain** sits in between: every note becomes a structured document with a fixed schema, every document is grep-able, every change is a Git commit. AI does the boring work of categorizing, deduplicating, and cross-linking — you just write notes the way you already do.

```
   raw notes (free-form)
            │
   ./brain notes/<file>.md
            │
   ┌────────┴────────┐
   │  AI normalize   │  → splits into PARA categories
   │  AI auto-merge  │  → updates existing docs instead of clobbering
   │  build-index    │  → refreshes navigation
   └────────┬────────┘
            │
   git commit
```

---

## PARA structure

```
knowledge-base/
├── 0-inbox/                  # Drop zone — delete after ingesting
├── 1-projects/               # Active initiatives with a goal & deadline
├── 2-areas/
│   ├── systems/              # Long-running things you're responsible for
│   ├── architecture/         # Patterns
│   │   └── adrs/             # Architecture Decision Records
│   └── teams/                # Org / team / process docs
├── 3-resources/
│   ├── concepts/             # Glossary, domain terms, definitions
│   └── playbooks/            # "How do I do X?" runbooks
├── 4-archives/               # Deprecated / completed
├── notes/                    # Raw inbound notes (kept as source-of-truth)
├── prompts/                  # Reusable AI prompt templates
├── templates/                # Markdown templates per document type
├── scripts/                  # Python scripts (normalize, index, validate)
├── ui/                       # Optional FastAPI dashboard
├── knowledge-index.md        # Auto-generated navigation
├── CHANGELOG.md              # Auto / manual log of KB changes
└── requirements.txt
```

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.9+ | `python3 --version` |
| Claude Code CLI | ≥ 2.1.79 | `claude --version` — must be authenticated locally |
| Git | any | for committing knowledge |

> Claude Code is the official Anthropic CLI: <https://docs.claude.com/en/docs/claude-code/overview>. Run `claude /login` once and you're set — no API keys to manage.

---

## Setup (5 minutes)

```bash
# 1. Use this template (or clone it)
git clone <your-fork-url> my-brain
cd my-brain

# 2. Install Python dependencies into a venv
python3 -m venv .venv
source .venv/bin/activate         # macOS / Linux / Git Bash
# .venv\Scripts\Activate.ps1      # Windows PowerShell
pip install -r knowledge-base/requirements.txt

# 3. Verify Claude is authenticated
claude --version
```

**Windows users:** the `./brain` and `./start` scripts are bash. Use Git Bash, WSL, or invoke the Python scripts directly (see "Manual usage" below). PowerShell wrappers `brain.ps1` and `start.ps1` are also provided.

---

## Daily workflow

### 1. Write a raw note

Drop any markdown file into `knowledge-base/notes/`. Free-form is fine — bullets, sentences, half-thoughts. No template required.

```bash
# Example
echo "Met with backend team. They use Postgres + Redis. Cache TTL is 5min..." \
  > knowledge-base/notes/2026-04-29-backend-sync.md
```

### 2. Ingest it

```bash
./brain knowledge-base/notes/2026-04-29-backend-sync.md
```

What happens:
1. **Normalize** — Claude splits the note into typed documents (system, concept, playbook, …).
2. **Auto-merge** — if a target file already exists, Claude merges the new info in instead of overwriting. Sources are appended, history preserved.
3. **Index** — `knowledge-index.md` is regenerated.

### 3. Review and commit

```bash
git diff
git add knowledge-base/
git commit -m "ingest backend sync notes"
```

That's the whole loop.

---

## The 6 document types

| Type | Use for | Required sections |
|---|---|---|
| `project` | Active initiatives with a goal | Goal · Status & Milestones · Related Knowledge |
| `system` | Things you operate / own long-term | Responsibility · Architecture · Key Behaviors · Dependencies · Debugging |
| `architecture` | Patterns / cross-cutting designs | Overview · When to Use · Advantages · Tradeoffs |
| `adr` | A specific decision, dated | Status · Context · Decision · Consequences |
| `concept` | Glossary / domain terms | Definition · Synonyms · Business Context |
| `playbook` | "How do I do X?" runbook | Problem · Investigation · Resolution · Prevention |
| `team` | Org / team / process | Responsibilities · Members · Related |

Templates live in [`knowledge-base/templates/`](knowledge-base/templates/). Every doc shares the same frontmatter:

```yaml
---
title: Cache Invalidation
type: concept
tags: [caching, backend]
updated: 2026-04-29
sources: [knowledge-base/notes/2026-04-29-backend-sync.md]
---
```

---

## Using with AI agents

This repo is designed to be read by AI agents (Claude Code, Cursor, Copilot, etc.).

### Entry point
`knowledge-base/knowledge-index.md` — load this first to get an overview.

### Skills (Claude Code)
If you use Claude Code, two skills are pre-wired in `.claude/skills/`:

- **`/brain-add`** — Ingest raw notes / text using the agent's native intelligence (no Python script needed). Respects PARA categorization, auto-merge, and source tracking.
- **`/brain-query`** — Forces the agent to search the KB before answering domain questions, citing files in its response.

### Prompt template
A reusable querying prompt is in [`knowledge-base/prompts/query-knowledge-base.md`](knowledge-base/prompts/query-knowledge-base.md).

### AGENTS.md
[AGENTS.md](AGENTS.md) is the integration contract for AI agents working in this repo (PARA rules, ingestion workflow, conventions). [CLAUDE.md](CLAUDE.md) is loaded automatically by Claude Code as project instructions.

---

## Manual usage (without the wrapper)

```bash
# Normalize a note (Auto-merges by default)
python3 knowledge-base/scripts/normalize_notes.py knowledge-base/notes/<file>.md

# Force overwrite (skip Auto-Merge)
python3 knowledge-base/scripts/normalize_notes.py knowledge-base/notes/<file>.md --overwrite

# Rebuild the index
python3 knowledge-base/scripts/build_index.py

# Find broken internal links
python3 knowledge-base/scripts/validate_links.py
python3 knowledge-base/scripts/validate_links.py --fix-suggestions

# Append a CHANGELOG entry
python3 knowledge-base/scripts/append_changelog.py \
  --summary "Onboarding sweep" \
  --added "2-areas/systems/payment-service.md: initial profile"

# Run the test suite
python3 -m pytest knowledge-base/scripts/tests/ -v
```

### Manual authoring (no AI)

```bash
cp knowledge-base/templates/system.md knowledge-base/2-areas/systems/my-service.md
$EDITOR knowledge-base/2-areas/systems/my-service.md
python3 knowledge-base/scripts/build_index.py
git add knowledge-base/ && git commit -m "add my-service profile"
```

---

## Optional: media ingestion (PDF & audio)

Two-step pipeline for non-markdown sources:

```bash
# Install extras
pip install pypdf openai-whisper ffmpeg-python

# 1. Convert to a raw note
python3 knowledge-base/scripts/media_ingest.py path/to/document.pdf
python3 knowledge-base/scripts/media_ingest.py path/to/meeting.mp3

# 2. Then ingest the resulting note
./brain knowledge-base/notes/ingested_<name>.md
```

---

## Optional: visual dashboard

A local FastAPI dashboard for browsing the KB:

```bash
./start
# then open http://localhost:8888
```

Features:
- Sidebar nav for the PARA tree
- Live markdown rendering with syntax highlighting
- Global fuzzy search
- Backlinks per document
- Optional graph view of cross-links

---

## Conventions

- **One concept per file** — if a doc grows past ~800 words, split it.
- **Lowercase kebab-case filenames** — `payment-service.md`, not `PaymentService.md`.
- **Commit = approved** — review with `git diff` before committing; no separate "draft" state.
- **Notes are not deleted** after normalization — they remain the raw source-of-truth and are referenced via the `sources:` array.
- **No secrets in notes** — content is sent to Claude. Strip credentials, tokens, and PII before ingesting.
- **English by convention** — keep KB documents in English so they remain searchable across teams. Raw notes can be in any language; the AI will translate during normalization.

---

## Non-goals

This template intentionally does **not** include:

- Vector embeddings or semantic search
- Cloud infrastructure or external SaaS
- A REST API or sync service
- Automatic deduplication across documents
- PII / secret scanning before ingestion (you do this)

All of the above add complexity without proportional benefit for a local-first single-user (or small-team) brain.

---

## Customizing the template

This is your brain — fork it freely. Common tweaks:

- **Rename categories** — Edit `ALLOWED_CATEGORIES` in `knowledge-base/scripts/normalize_notes.py` and `CATEGORY_HEADINGS` in `knowledge-base/scripts/build_index.py`.
- **Change the prompt** — `NORMALIZE_PROMPT_TEMPLATE` in `normalize_notes.py` controls how Claude splits notes.
- **Add document types** — Add a template in `knowledge-base/templates/`, then update the prompt's "Document types" section.
- **Per-domain skills** — Edit `.claude/skills/brain-query/SKILL.md` to bias the agent toward specific files (e.g., a curated "lens" doc).

---

## License

MIT — do whatever you want, no warranty.
