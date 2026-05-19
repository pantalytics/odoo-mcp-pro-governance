# ADR-011: One role per API key, not many

**Status:** Accepted (2026-05-19)
**Depends on:** [ADR-010](010-api-key-bound-to-role.md)

## Context

OCA `base_user_role` lets a **user** hold multiple roles at once (`role_line_ids` is One2many). When `set_groups_from_roles()` runs, the user's `groups_id` becomes the union of all their roles' groups. Roles are **additive** at the user level.

For API keys we had to pick: mirror OCA (Many2many, additive) or use a single role (Many2one, exclusive).

| | Many-to-one (chosen) | Many-to-many (OCA-style) |
|---|---|---|
| Mental model | "This key is for purpose X" | "This key can do X + Y" |
| Operator work | Occasionally define a combo role | Tick checkboxes |
| Least-privilege risk | Lower — explicit scoping | Higher — easy to over-grant via stacking |
| UX in wizard | Dropdown | Many2many tags widget |
| Match with OCA's user pattern | Diverges | Mirrors |

## Decision

**One role per API key.** `res.users.apikeys.x_role_id` is a `Many2one` to `res.users.role`.

If an operator needs a key that spans multiple capability buckets, they create a role that combines those buckets (composing groups in the role's Groups tab), then assign that single role to the key.

## Consequences

**Positive**
- Forces a deliberate scope decision at key creation time. "What is this key for?" has a single answer.
- Lower blast radius if a key leaks: exactly the scope of one named role, not a union of several roles whose intersection no operator may have audited.
- Simpler enforcement in our `_check_credentials` / `_has_group` / `ir.model.access.check` overrides: one role lookup per request, no union-set math.
- Clear audit trail: every call's `auditlog.http.request` row maps back to one role identity, not an N-tuple.

**Negative**
- Some setups need a combo role like "CRM Reader + Audit Reader". Operator has to create it explicitly. Friction.
- Diverges from OCA's user-level pattern. Operators familiar with `base_user_role` may initially expect tag-style stacking and find the single dropdown unexpected.
- If `base_user_role` ever ships a wizard to "create a role from N existing roles", we benefit; until then operators do it manually.

## Alternatives considered

- **Many2many (OCA-style additive)** — rejected for least-privilege reasons above. Could revisit if operator feedback says "we constantly need combo roles."
- **No role at all on key, derive from user's role bag** — rejected because then a key's permission surface = the union of ALL roles the user holds. Worse than the Many2many option; a maintenance update to one role propagates to every key under that user.

## Notes on live propagation (the question that prompted this ADR)

Editing a role's groups propagates immediately to all keys bound to that role. Our `_check_credentials` reads the role from the DB on every authenticated request and expands `role.group_id ∪ role.implied_ids` live; no caching on our side. OCA's own `set_groups_from_roles()` runs on every role write/unlink, which clears Odoo's standard caches that the parent path would have hit. The combined effect: change a role at 14:00, the next API call from a bound key at 14:00:01 sees the new permissions. No container restart, no manual cache flush.
