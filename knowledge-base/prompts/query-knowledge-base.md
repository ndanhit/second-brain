---
title: Query Knowledge Base
type: prompt
tags:
  - ai-agent
  - retrieval
updated: 2026-04-29
---

# Query Knowledge Base

A reusable prompt template for AI agents (or engineers using Claude Code) to read and reason over this knowledge base.

## Prompt Template

```
You are a helpful assistant with access to this repository's knowledge base.

To answer the question below, follow these steps:
1. Read `knowledge-base/knowledge-index.md` to get an overview of all available documents.
2. Identify which documents are relevant to the question based on their titles and tags.
3. Read those specific documents in full.
4. Answer the question using only information from the documents you have read.
   If the answer is not in the knowledge base, say so clearly.

Question: {question}
```

## Example Usage in Claude Code

Open a Claude Code session in this repository and ask:

```
Using the knowledge base, answer: How does our payment retry policy work?
```

Claude will:
1. Read `knowledge-base/knowledge-index.md` to find relevant documents.
2. Navigate to the matching `2-areas/systems/...` or `3-resources/playbooks/...` files.
3. Answer based on the documented content, citing file paths.

## Tips for AI-Friendly Querying

- Start with `knowledge-base/knowledge-index.md` — it lists all documents with tags for fast relevance scanning.
- Each document covers a single concept across the PARA categories: projects, systems, architecture (incl. ADRs), concepts (incl. glossary), playbooks, teams.
- Follow cross-links `[Term](../...md)` within documents to navigate deeply into related contexts.
- Document types:
  - `playbook`: "How do I debug / handle X?"
  - `system`: "What does X do?"
  - `architecture`: "Why is X designed this way?"
  - `adr`: "What was the specific technical decision made for X?"
  - `project`: "What is the goal and current status?"
  - `concept`: "What does this term mean in our domain?"
  - `team`: "Who owns this process or system?"
- The `updated` frontmatter field helps identify whether documentation is current.
