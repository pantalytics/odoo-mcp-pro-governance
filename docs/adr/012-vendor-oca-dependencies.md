# ADR-012: Vendor OCA dependencies into the repo

**Status:** Superseded by [ADR-013](013-rename-vendored-modules.md) (2026-05-20)
**Supersedes:** the implicit assumption in [ADR-002](002-depend-on-oca-auditlog.md) and [ADR-010](010-api-key-bound-to-role.md) that customers would resolve OCA dependencies via their own addons path.
**Implemented in:** v0.5.0 → v1.0.0. **Replaced by the renamed-bundle approach in v1.2.0.**

> **Why superseded:** the diagnostic in this ADR proved that
> apps.odoo.com refreshes a listing whose `depends` references unknown
> modules. It did **not** test what happens when we actually try to
> upload the bundle. When v1.0.0 went up, apps.odoo.com rejected the
> upload: "Module auditlog already exists for another serie. Please
> select a free module name or use the right user account." The names
> are claimed by OCA for older Odoo series, so we cannot upload under
> them. The fix is in [ADR-013](013-rename-vendored-modules.md).

## Context

`pan_mcp_pro_governance` depends on two OCA modules: `auditlog` (audit
trail, [ADR-002](002-depend-on-oca-auditlog.md)) and `base_user_role`
(roles, [ADR-010](010-api-key-bound-to-role.md)). Until v0.4 we listed
both in our manifest's `depends` and expected customers to add them to
their addons path separately (Odoo.sh submodule, manual clone, etc).

The publisher portal at apps.odoo.com refuses to refresh a listing
whose manifest `depends` names a module not present in its own 19.0
module index. Neither `auditlog` nor `base_user_role` is on
apps.odoo.com for 19.0 — they live on apps.odoo-community.org and
GitHub OCA. apps.odoo.com surfaces a yellow warning ("unmet dependency
X for series 19.0. Dependency might be invalid.") that, despite its
yellow colour, is in fact a hard blocker: the listing content stays
frozen on whatever was published before any unmet dep appeared.

We verified this directly. Diagnostic commits 19.0.0.4.2 and 19.0.0.4.3
removed `auditlog` then `base_user_role` from `depends` one at a time
and watched the apps.odoo.com page. With both OCA deps gone (and only
`base` and `mail` declared) the listing content finally refreshed to
v0.4.3.

We need to publish via apps.odoo.com. The whole strategic point of
keeping the listing fresh is the SEO funnel ("MCP" keyword → our
listing → pantalytics.com/apps/odoo-mcp-server SaaS). Hosting on
apps.odoo-community.org would isolate us from that traffic.

## Decision

Vendor the two OCA modules into this repository as **bundled sibling
addons** at the root level (alongside `pan_mcp_pro_governance/`), and
restore them to `depends`. apps.odoo.com finds the modules within the
same upload, the listing refresh works, and customers get a
single-click install that pulls in all three addons.

Specifically:

- `/auditlog/` — verbatim copy of OCA `server-tools/auditlog` at
  `19.0.1.0.1`. No modifications.
- `/base_user_role/` — verbatim copy of OCA
  `server-backend/base_user_role` at `19.0.1.0.2`. No modifications.
- [`NOTICE.md`](../../NOTICE.md) at repo root: explicit attribution,
  origin URLs, copyright holders, licences.
- The vendored folders keep their own `LICENSE`, `README.rst` and
  `__manifest__.py` (author = "ABF OSIELL, Odoo Community Association
  (OCA)") so attribution is preserved at the package level too.

## Consequences

**Positive**
- apps.odoo.com listing updates work. The SEO/funnel goal is served.
- Customers see one-click install. Odoo auto-installs the two
  dependencies from the same upload.
- Attribution is honest: vendored folders are untouched, licences and
  copyright headers preserved, NOTICE.md tells the full story.
- If a customer already has OCA's official versions on their addons
  path, Odoo's first-match resolution uses those instead of our
  copies — they're not forced to use ours.

**Negative**
- Repository grows by ~30 files of code we didn't write.
- Maintenance burden: when OCA releases a new version we re-vendor by
  wholesale folder replacement (see NOTICE.md). Diff-patching is
  forbidden by policy because it would amount to forking.
- Customers see three modules in their Apps menu instead of one.
  Mitigated by listing copy explaining the bundle.
- Vendoring OCA code in a non-OCA repo is mildly frowned on by the
  community. Mitigation: we don't claim authorship; NOTICE.md and the
  preserved upstream manifests credit OCA loudly.
- AGPL combined-work rule means our addon distribution as a whole must
  remain AGPL-3, which it already is.

## Alternatives considered

- **Forking the OCA modules into a single monolith** (merge models into
  `pan_mcp_pro_governance`): rejected. Heavy code-intertwining, AGPL
  copyright-header bookkeeping in every file, much harder to roll
  forward when OCA fixes a bug.
- **Rewriting our own audit trail + role machinery from scratch**:
  rejected. Weeks of work for code that already exists and is
  battle-tested in OCA. We'd also lose the "stand on the shoulders of
  OCA" credibility.
- **Distributing only via apps.odoo-community.org**: rejected. We
  forfeit the SEO/funnel benefit of being on the official apps.odoo.com
  for the "MCP" keyword.
- **Lobbying apps.odoo.com to accept OCA deps**: out of scope. Odoo
  SA's dependency policy is unlikely to change for our submission.

## Operational notes

- The vendored folders are not edited locally; any change in upstream
  goes through wholesale folder replacement.
- Each vendored module's version is pinned to a specific OCA release.
  Bumping `pan_mcp_pro_governance`'s own version does not implicitly
  bump the vendored ones.
- When customers report bugs in audited behaviour or role-binding, we
  triage whether the issue is in OUR code (the bundled `auditlog` /
  `base_user_role` are stock OCA) or in OCA's upstream. If upstream,
  point them at the OCA issue tracker.

## Sources

- Diagnostic commits: `8ae5aad` (manifest scan triggered), `2e75bef`
  (drop `auditlog`, warning shifted), `443266d` (drop `base_user_role`,
  listing finally refreshed).
- apps.odoo.com publisher portal behaviour observed 2026-05-20.
- OCA `auditlog` 19.0.1.0.1: <https://github.com/OCA/server-tools/tree/19.0/auditlog>
- OCA `base_user_role` 19.0.1.0.2: <https://github.com/OCA/server-backend/tree/19.0/base_user_role>
