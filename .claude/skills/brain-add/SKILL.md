---
name: brain-add
description: Add raw notes or text content to the user's Second Brain by normalizing them into PARA structure.
---

# brain-add

Use this skill to transform raw notes, transcripts, or text into structured knowledge documents directly using your own intelligence, ensuring strict adherence to the project's PARA structure and documentation policies.

## Workflow

1. **Analyze Content**: Carefully read the input text or file.
2. **Categorize & Structure**:
   - Identify distinct concepts, systems, projects, teams, playbooks, ADRs mentioned.
   - Map them to the PARA categories (`1-projects`, `2-areas/systems`, `2-areas/architecture`, `2-areas/architecture/adrs`, `2-areas/teams`, `3-resources/concepts`, `3-resources/playbooks`).
   - Apply the corresponding template from `knowledge-base/templates/` (frontmatter: `title`, `type`, `tags`, `updated`, `sources`).
   - **Policy — Sources**: The `sources` array MUST use project-relative paths (e.g., `knowledge-base/notes/filename.md`). If the input is a file outside the project, **copy it to `knowledge-base/notes/`** first before referencing it.
   - **Policy — Cross-linking**: Use relative paths (e.g., `[System X](2-areas/systems/system-x.md)`) for internal links.
   - **Policy — Filenames**: Lowercase kebab-case (`my-system.md`, not `MySystem.md`).
3. **Merge Check (Collision Handling)**:
   - Before writing, check if the target file already exists.
   - If it exists, **read it first** and merge new information into it, preserving existing context. Never delete prior content unless the new note explicitly deprecates it.
   - Append the new note path to the `sources` array; bump `updated` to today.
4. **Write Files**: Save the structured markdown files to their respective locations.
5. **Index Refresh**: Always run `python3 knowledge-base/scripts/build_index.py` after writing any files.

## Example usage

- "Add this note to my brain: [content]"
- "Process this download: /path/to/download.md"
- "Sync my brain with this text: [text]"
