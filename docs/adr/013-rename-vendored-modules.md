# ADR-013: Rename bundled OCA modules under a Pantalytics prefix

**Status:** Accepted (2026-05-20)
**Supersedes:** [ADR-012](012-vendor-oca-dependencies.md) — the bundled-sibling approach under OCA's original names.
**Implemented in:** v1.2.0

## Context

[ADR-012](012-vendor-oca-dependencies.md) vendored OCA `auditlog` and
`base_user_role` into this repository as sibling folders under their
canonical OCA names, and listed those names in `pan_mcp_pro_governance`'s
manifest `depends`. The diagnostic in that ADR confirmed apps.odoo.com
*would refresh the listing* with this layout. We treated that as proof
the bundle would work.

When v1.0.0 went up for upload to apps.odoo.com, the publisher portal
returned three errors:

```
Module auditlog already exists for another serie. Please select a free module name or use the right user account.
Module base_user_role already exists for another serie. Please select a free module name or use the right user account.
pan_mcp_pro_governance: unmet dependency auditlog for series 19.0. Dependency might be invalid.
```

apps.odoo.com enforces **global module-name uniqueness across all
publishers**, not just within a single publisher's listings. OCA has
registered `auditlog` and `base_user_role` for series 17.0 and 18.0 —
both names are reserved indefinitely, even though OCA has not yet
published 19.0 versions. We cannot upload anything under those names
from a different publisher account, *and* our 19.0 listing's
`depends: ['auditlog', 'base_user_role']` cannot be satisfied because
the 19.0 module index does not contain those names.

The ADR-012 verification only checked the *listing refresh* path
(removing `depends` entries makes the warning disappear). It did not
test the *bundle upload* path, where the names collide upstream of
our own publisher account.

## Decision

Rename the vendored modules under a Pantalytics prefix:

- `auditlog/` → `pan_mcp_auditlog/`
- `base_user_role/` → `pan_mcp_user_role/`

`pan_mcp_pro_governance/__manifest__.py` `depends` now lists the new
slugs. The Python source, model technical names (`auditlog.rule`,
`auditlog.log`, `res.users.role`, …), upstream copyright headers,
licences, and authors stay untouched. The only modifications inside
the renamed folders are:

1. The folder name itself.
2. The manifest `name` display field, suffixed with " (Pantalytics
   bundle)" so the Apps menu distinguishes our copies from OCA's
   originals.
3. Same-module XML refs that used full qualification
   (`ref('auditlog.group_auditlog_user')`) updated to the new prefix
   (`ref('pan_mcp_auditlog.group_auditlog_user')`).

XML record IDs inside `pan_mcp_pro_governance/` that previously
referenced the OCA records as `auditlog.x` or `base_user_role.x` also
got the new prefix.

## Consequences

**Positive**

- apps.odoo.com accepts the upload. No name conflict, listing refreshes,
  Deploy on Odoo.sh delivers all three modules.
- Pantalytics fully owns the module slugs `pan_mcp_auditlog` and
  `pan_mcp_user_role`. Future updates require no further negotiation
  with OCA or apps.odoo.com.
- The OCA authorship and licence are still preserved at the package
  level (manifest `author`, `LICENSE`, README.rst) so the rename does
  not erase attribution. [NOTICE.md](../../NOTICE.md) explains the
  reason for the prefix.

**Negative**

- **No coexistence with OCA originals.** A customer who already has
  OCA's `auditlog` or `base_user_role` installed in the same database
  cannot install the Pantalytics bundle on top. Both define the same
  Python models (`auditlog.rule`, `res.users.role`, …) and Odoo will
  refuse to register them twice. Customers in this situation must
  pick one source; the choice is documented in NOTICE.md and
  install.md.
- **Mild rename drift in the renamed folders.** ADR-012's "verbatim
  copy, never edited" policy is relaxed. The accepted edits are
  enumerated above. Anything else still triggers wholesale
  re-vendoring.
- **Locked-in fork.** If OCA later publishes a 19.0 `auditlog` and
  `base_user_role` to apps.odoo.com, we would in principle be able to
  switch our `depends` back to the upstream names — but only if we
  remove the renamed copies first to avoid model-name collisions.
  Coordinating that for installed customers is a migration in itself,
  and would likely warrant a major version bump.

## Alternatives considered

- **Rename Python model names too (heavy refactor).** Would allow
  coexistence with OCA originals (each package would own distinct
  model namespaces like `pan_mcp_auditlog.rule`). Rejected for v1.2.0
  because it touches dozens of files in pan_mcp_pro_governance + the
  bundled folders, requires a DB migration for any existing
  installs, and the coexistence benefit only helps the small slice of
  Route C self-hosted customers who already have OCA originals. We
  may revisit if that population grows.
- **Wait for OCA to publish 19.0 versions to apps.odoo.com.**
  Timeline unknown, fully outside our control, and the SEO funnel
  argument from ADR-012 still applies — we cannot afford to delay
  the listing.
- **Drop the OCA dependency entirely (ship a stripped listing).**
  The current live v1.0.0 listing is exactly this — `depends` only
  on `base` and `mail`. The audit log and role-binding features
  silently degrade because the OCA models don't exist. Acceptable as
  an emergency status quo but not as a real product.
- **Distribute only via GitHub.** Loses the apps.odoo.com SEO funnel,
  which was the original reason for the bundling effort.

## Operational notes

- The rename does **not** require a DB migration script. Model
  technical names and table names are unchanged, so existing installs
  of OCA `auditlog` / `base_user_role` on the same DB would still own
  their tables; the conflict is at *install time* when Odoo tries to
  register the same model twice.
- For v1.0.0 → v1.2.0 upgrades on existing GitHub-installed databases:
  the bundle was never on apps.odoo.com, so the user base is small.
  An upgrade essentially means uninstall the old (`auditlog` /
  `base_user_role` rows in `ir_module_module` go inactive when those
  folders disappear from addons_path) and install the new
  (`pan_mcp_auditlog` / `pan_mcp_user_role`). Manually documented in
  install.md.
- Refreshing the bundle from new OCA releases: same as ADR-012, plus
  one extra step — re-apply the manifest `name` suffix and the
  same-module XML ref prefix changes after copying the upstream
  folder.

## Sources

- apps.odoo.com publisher portal error messages observed 2026-05-20.
- ADR-012 diagnostic commits and the partial-verification gap it
  uncovered.
- OCA `auditlog` 19.0.1.0.1: <https://github.com/OCA/server-tools/tree/19.0/auditlog>
- OCA `base_user_role` 19.0.1.0.2: <https://github.com/OCA/server-backend/tree/19.0/base_user_role>
