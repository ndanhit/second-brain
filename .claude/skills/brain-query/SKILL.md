---
name: brain-query
description: Search the user's Second Brain knowledge base before answering domain questions. Use when the user asks about any concept, system, project, team, playbook, or term that may be captured in their KB — so answers cite the KB instead of general knowledge.
---

# brain-query

Use this skill whenever the user asks a factual question that could plausibly be answered from their personal knowledge base. Search the KB in priority order and answer from cited content before falling back to general knowledge.

## When to invoke

**Trigger phrases** (non-exhaustive):
- "What is …", "Who is …", "Tell me about …" for any term that sounds domain-specific.
- "How does X work in our system / project?"
- "What's the goal / status of …?"
- Any acronym or short label that looks like internal jargon.
- Questions about internal processes, tools, decisions (ADRs), or playbooks.

**Do NOT invoke** for:
- Pure coding/implementation questions unrelated to the user's documented domain.
- General-knowledge questions clearly outside the KB's scope.

## Workflow

1. **Scan the index** — read `knowledge-base/knowledge-index.md` to find candidate documents by title and tags.
2. **Search in priority order**:
   1. **Concepts / Glossary** (`knowledge-base/3-resources/concepts/`) — short defs and acronyms.
   2. **Systems, architecture, ADRs, teams** (`knowledge-base/2-areas/`) — durable domain knowledge.
   3. **Projects** (`knowledge-base/1-projects/`) — current goals and status.
   4. **Playbooks** (`knowledge-base/3-resources/playbooks/`) — operational guides.
   5. **Raw notes** (`knowledge-base/notes/`) — only if nothing found in structured docs.
   6. **Archive** (`knowledge-base/4-archives/`, `knowledge-base/notes/_archive/`) — historical lookups.
3. **Answer with citations** — cite the relative file path (e.g., `3-resources/concepts/my-term.md`) so the user can verify.
4. **Flag gaps** — if the KB has no answer, say so explicitly before answering from general knowledge. This prevents silently mixing user-curated facts with external assumptions.
5. **Suggest capture** — if the user volunteers new information during Q&A, offer to run `/brain-add` to save it.

## Output Shape

```
<answer>

Source(s):
- path/to/kb-file.md (section if relevant)

[if applicable] Gap: <what the KB doesn't cover>
```

## Why this skill exists

The user has built a curated, factual KB. Answers should reflect THEIR captured truth (with dates and sources), not the model's training data. This skill enforces that discipline.
