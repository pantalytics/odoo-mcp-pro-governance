# Documentation

End-user help for this module lives in **Odoo Knowledge** (`pantalytics.odoo.com` → Help → MCP Pro Governance). Knowledge is the single source of truth — edit articles there, not here. This folder is for developer-facing material only.

The Pantalytics website does **not** host docs — only marketing and the app listing.

## Why Knowledge is master

We tried the inverse (markdown master, sync to Knowledge) and dropped it: maintaining two copies of the same article was double work, and the sync direction made it tempting to edit Knowledge directly and lose changes on next sync. Knowledge has WYSIWYG editing, attachments, embedded views, and is already where the Helpdesk chatbot reads from. The markdown round-trip added cost without value.

Decided 2026-05-22. See the corresponding memory entry.

## What lives here

```
docs/
├── dev/        ← Developer / technical reference (design rules, feedback loops,
│                 internal write-ups, screenshots). GitHub-only.
├── adr/        ← Architecture Decision Records. GitHub-only.
├── research/   ← Background research, positioning notes. GitHub-only.
└── user/       ← Empty by intent. Migration parking only.
```

`docs/user/` is kept as a folder so legacy links don't 404 outright, but new end-user content goes into Knowledge directly. If a file lingers here it's because it hasn't been migrated yet — flag it, port it to Knowledge, then delete the markdown.

## Linking to Knowledge from code

Inline help in views and Python code should link to the **public Knowledge article URL**:

```
https://pantalytics.odoo.com/knowledge/article/<id>
```

The article id is database-stable on `pantalytics.odoo.com`. If we ever recreate an article it gets a new id, so re-grep the codebase for the old number and update the references. Article ids in code should be rare — only used where the inline UX cannot reasonably explain the concept on its own.

For internal docs (this folder), use relative paths (`[the design rules](dev/design.md)`).

## See also

- [CLAUDE.md](../CLAUDE.md) — project context for AI assistants.
- [dev/design.md](dev/design.md) — UI design philosophy for this module.
- [dev/FEEDBACK.md](dev/FEEDBACK.md) — how to validate your changes.
