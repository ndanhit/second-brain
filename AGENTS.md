# AGENTS.md — AI Agent Integration Guide

This document defines how AI agents (Claude Code, Cursor, GitHub Copilot, Antigravity, etc.) should interact with this **second-brain** repository to maintain structural integrity and knowledge consistency.

---

## Mission

Maintain a high-fidelity, local-first knowledge base. Every piece of information added must be **structured, cross-linked, and persistent** — never lost, never duplicated, always traceable back to its source.

## Knowledge Structure (PARA)

Place documents in the correct numbered folder. **Always**:

0. **`0-inbox/`** — Temporary drop zone for unprocessed notes. Delete after ingesting.
1. **`1-projects/`** — Active initiatives with a goal and a finite horizon.
2. **`2-areas/`** — Long-term responsibilities.
   - `systems/` — Software components, services, owned things.
   - `architecture/` — Design patterns, cross-cutting concerns.
   - `architecture/adrs/` — Architecture Decision Records (`ADR-NNNN: title`).
   - `teams/` — Org structures, processes, culture.
3. **`3-resources/`** — Domain knowledge.
   - `concepts/` — Glossary, terminology, definitions.
   - `playbooks/` — Operational guides and troubleshooting.
4. **`4-archives/`** — Completed or deprecated knowledge.

## Ingestion Workflow (adding knowledge)

When the user provides raw text or a note file, pick the most appropriate path:

### A. Use the `/brain-add` skill (recommended for Claude Code)
The skill in `.claude/skills/brain-add/` instructs the agent to do the work natively — no subprocess, no JSON schema round-trip. Most reliable when supported.

### B. Run `./brain <path_to_note>`
The shell script orchestrates `normalize_notes.py` (calls Claude with a fixed prompt + JSON schema) and `build_index.py`. Use when you need deterministic, scripted behavior.

### C. Manual write — only if neither A nor B fits

If you write files manually, you **MUST**:

1. **Check for existing files** — search for the target filename across `knowledge-base/**/*.md` first.
2. **Auto-merge on collision** — read the existing file, integrate new info into its sections, **never delete prior context** unless the new note explicitly deprecates it.
3. **Use templates** — copy frontmatter and section headings from `knowledge-base/templates/<type>.md`.
4. **Track sources** — the `sources:` array MUST list project-relative paths. If the source file lives outside the repo, **copy it into `knowledge-base/notes/` first**, then reference that path.
5. **Cross-link** — every mention of another system / concept / project must be a relative markdown link, e.g., `[Payment Service](2-areas/systems/payment-service.md)`.
6. **Refresh the index** — run `python3 knowledge-base/scripts/build_index.py` after any write.

## Querying Workflow (retrieving knowledge)

To answer questions accurately:

1. **Scan the index** — read `knowledge-base/knowledge-index.md` first to find candidate filenames by title and tag.
2. **Deep read** — open the specific `.md` files identified.
3. **Trace sources** — if a document is too brief, follow its `sources:` array to the raw notes for more context.
4. **Cite paths** — always cite the relative file path so the user can verify (`3-resources/concepts/cache-invalidation.md`).
5. **Flag gaps** — if the KB doesn't cover the question, say so explicitly before answering from general knowledge.

## Principles & Constraints

- **Atomic documents** — one concept per file. If a file exceeds ~1000 words, suggest splitting it.
- **Lowercase kebab-case filenames** — `payment-gateway.md`, not `PaymentGateway.md`.
- **Markdown only** — no binary formats, no external databases. Plain text wins.
- **Local-first** — do not introduce vector search, cloud sync, or external services without explicit user approval.
- **English by default** — KB documents stay in English so they remain portable across teams. Raw notes in `notes/` may be in any language; translate during normalization.
- **Frontmatter is contract** — every doc has `title`, `type`, `tags`, `updated`, `sources`. Don't omit fields.
- **Sources are append-only** — when merging, **add** the new note path to `sources:`, never replace.

---

*This file is internal documentation for AI agents. If you are an agent reading this, acknowledge these rules and proceed accordingly.*
