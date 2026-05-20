# NOTICE — Third-party software bundled in this repository

`pan_mcp_pro_governance` distributes two unmodified copies of community
Odoo modules from the **Odoo Community Association (OCA)** alongside its
own code, under renamed module slugs. This file makes the origin,
copyright, and licence of those bundled modules explicit, as required
by AGPL-3.

## Why these modules are bundled under renamed slugs

`pan_mcp_pro_governance` needs `auditlog` (audit trail) and
`base_user_role` (role-based access). OCA has not published a 19.0
version of either to apps.odoo.com, but the names `auditlog` and
`base_user_role` are already registered there for older Odoo series
(17.0, 18.0). apps.odoo.com's publisher portal refuses to accept new
uploads under those names from a different publisher, *and* it refuses
to refresh our listing when our `__manifest__.py` `depends` references
names that have no 19.0 entry in its module index.

To unblock distribution via apps.odoo.com (and the "Deploy on Odoo.sh"
button), the two OCA modules are vendored into this repository under
**renamed slugs**: `pan_mcp_auditlog` and `pan_mcp_user_role`. The
Python code, model technical names (`auditlog.rule`, `res.users.role`,
…), upstream copyright headers, licences, and authors are untouched —
only the module folder + `__manifest__.py` `name` field changed.

The fuller rationale, alternatives considered, and the migration path
are documented in
[`docs/adr/013-rename-vendored-modules.md`](docs/adr/013-rename-vendored-modules.md),
which supersedes
[`docs/adr/012-vendor-oca-dependencies.md`](docs/adr/012-vendor-oca-dependencies.md).

## Bundled addons

### `pan_mcp_auditlog/`

- **Origin**: https://github.com/OCA/server-tools/tree/19.0/auditlog
- **Upstream slug**: `auditlog`
- **Version vendored**: `19.0.1.0.1`
- **Copyright**: © 2015 ABF OSIELL <https://osiell.com> · © Odoo Community Association (OCA)
- **Licence**: AGPL-3.0 or later (LICENSE file lives in the vendored folder)
- **Modifications**: only the folder name and `__manifest__.py`
  `name` display label changed. Python source, model names, data files,
  views, security rules — all verbatim from upstream.

### `pan_mcp_user_role/`

- **Origin**: https://github.com/OCA/server-backend/tree/19.0/base_user_role
- **Upstream slug**: `base_user_role`
- **Version vendored**: `19.0.1.0.2`
- **Copyright**: © 2014 ABF OSIELL <https://osiell.com> · © Odoo Community Association (OCA) · © Tecnativa · © Camptocamp
- **Licence**: LGPL-3.0 or later (LICENSE file lives in the vendored folder)
- **Modifications**: same as `pan_mcp_auditlog/` — folder name and
  manifest display label only.

## Coexistence with the upstream OCA modules

The bundled copies keep the OCA Python model names (`auditlog.rule`,
`res.users.role`, etc). If a customer already has the official OCA
`auditlog` or `base_user_role` modules installed (e.g. via their own
clone of `OCA/server-tools` on the addons path), installing the
Pantalytics bundle on top will fail with a model-registration conflict.
Customers in that position should choose one of:

1. **Use the OCA originals**: remove the bundled folders from the
   `addons_path` and edit `pan_mcp_pro_governance/__manifest__.py` to
   list the upstream slugs (`auditlog`, `base_user_role`) under
   `depends`. Reinstall.
2. **Use the Pantalytics bundle**: uninstall the OCA originals first,
   then install MCP Pro from this repository.

For fresh Odoo installs — including every "Deploy on Odoo.sh" flow from
apps.odoo.com — option 2 is the default and works without
configuration.

## Licence compatibility

- `pan_mcp_pro_governance` is **AGPL-3.0-or-later**.
- `pan_mcp_auditlog` is **AGPL-3.0-or-later** (matches upstream) — same
  licence as the parent addon, no friction.
- `pan_mcp_user_role` is **LGPL-3.0-or-later** (matches upstream) —
  LGPL is compatible with AGPL when combined; the combined work as a
  whole is governed by AGPL-3.

## How to refresh the bundled copies

When OCA releases new versions of either module:

```bash
# from the repo root
rm -rf pan_mcp_auditlog/ pan_mcp_user_role/
git clone --depth 1 --branch 19.0 https://github.com/OCA/server-tools.git /tmp/oca-st
git clone --depth 1 --branch 19.0 https://github.com/OCA/server-backend.git /tmp/oca-sb
cp -R /tmp/oca-st/auditlog ./pan_mcp_auditlog
cp -R /tmp/oca-sb/base_user_role ./pan_mcp_user_role
rm -rf /tmp/oca-st /tmp/oca-sb
# then in each renamed folder's __manifest__.py, change the "name"
# field display label to "Audit Log (Pantalytics bundle)" /
# "User Roles (Pantalytics bundle)" so the Apps menu makes the bundling
# obvious
# update NOTICE.md with the new versions; commit
```

The vendored copies must never be edited locally beyond the folder
rename and the display-name tweak. If a code fix is needed, file an
issue or PR with OCA and roll the upstream change forward when it is
merged.

## Contact

For licence questions: <support@pantalytics.com>
For OCA source authority: <https://odoo-community.org>
