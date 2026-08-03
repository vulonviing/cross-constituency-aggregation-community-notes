---
name: paper-idea-capture
description: Capture user-approved research and writing ideas for the active Community Notes paper as timestamped markdown notes. Use when discussing manuscript framing, arguments, citations, methods, results, figures, limitations, or future paper ideas, especially when the user asks to save an idea or accepts an agent proposal to save one.
---

# Paper Idea Capture

Use this skill to preserve useful ideas that arise while discussing the active
paper. The goal is a lightweight idea trail, not a second manuscript draft.

## Workflow

1. Notice promising ideas about the active manuscript, including framing,
   arguments, citations, methods, results, figures, limitations, or future work.
2. Do not write a note automatically. Briefly propose saving the idea, or write
   it only when the user explicitly asks or approves.
3. Store approved notes under:
   `paper/03-07-2026-1550-edition/idea-notes/`
4. Name each file with local time and a short discussion title:
   `YYYY-MM-DD-HHMM-title-slug.md`
5. Use a lowercase ASCII slug with hyphens. Remove punctuation. If the filename
   already exists, append `-2`, `-3`, and so on.
6. Keep the note concise and useful for later paper writing. Use the
   conversation language unless the user asks for English or provides
   manuscript-ready English.
7. Respect all repository rules in `AGENTS.md`, including step logging after
   meaningful work.

## Note Template

```markdown
# <Discussion Title>

- **Date:** YYYY-MM-DD HH:MM +/-TZ
- **Source:** Paper discussion

## Context
<What prompted the idea.>

## Idea
<The core idea to preserve.>

## Why It Matters
<How it could improve the paper.>

## Follow-up
<Concrete next step, open question, or section where it belongs.>
```
