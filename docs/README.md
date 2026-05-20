# Documentation

This folder is the **master source of truth** for all documentation related to this module. From here, end-user content is synced one-way to Odoo Knowledge for public consumption and the Helpdesk chatbot. The Pantalytics website does **not** host docs — only marketing and the app listing.

## Structure

```
docs/
├── user/       ← End-user help. Synced to Odoo Knowledge.
├── dev/        ← Developer / technical reference (design rules, feedback loops,
│                 internal write-ups, screenshots). GitHub-only, never synced.
├── adr/        ← Architecture Decision Records. GitHub-only.
└── research/   ← Background research, positioning notes. GitHub-only.
```

**Sync rule is path-based:** `docs/user/**` syncs to Knowledge, everything else stays GitHub-only. Anything internal goes in `docs/dev/` — do not drop loose `.md` or screenshot files at the top level of `docs/`.

## Authoring rules

- Markdown only. Write in your editor of choice; Claude edits these files directly.
- Files in `docs/user/` need frontmatter:

  ```yaml
  ---
  title: How to connect Claude to Odoo
  knowledge_article_id:   # filled in after first sync, leave blank for new files
  last_synced:            # filled in by the sync tool
  ---
  ```

- Internal cross-links: relative paths (`[the design rules](../dev/design.md)`).
- External links: only to canonical Pantalytics URLs or upstream Odoo/OCA docs. No tracking parameters.

## Sync direction is one-way

GitHub → Odoo Knowledge. **Never edit synced articles in the Odoo UI** — the next sync will overwrite your changes. If you need a non-developer to edit, accept their change as a PR or commit it yourself.

## When removing legacy docs from pantalytics.com

301-redirect the old URL to the new Knowledge article URL (or to the corresponding `docs/user/` path rendered via GitHub Pages). Never let an existing docs URL 404 — you lose the SEO equity built up on the old post.

## See also

- [CLAUDE.md](../CLAUDE.md) — project context for AI assistants.
- [dev/design.md](dev/design.md) — UI design philosophy for this module.
- [dev/FEEDBACK.md](dev/FEEDBACK.md) — how to validate your changes.
