# NOTICE — Third-party software bundled in this repository

`pan_mcp_pro_governance` distributes two unmodified copies of community
Odoo modules from the **Odoo Community Association (OCA)** alongside its
own code. This file makes the origin, copyright, and licence of those
bundled modules explicit, as required by AGPL-3.

## Why these modules are vendored

`pan_mcp_pro_governance` depends on `auditlog` (audit trail) and
`base_user_role` (role-based access). Both are published by OCA but are
*not* present in the apps.odoo.com module index for Odoo 19, which
prevents the apps.odoo.com publisher portal from updating the listing
when those names appear in our `__manifest__.py` `depends`. To distribute
this addon via apps.odoo.com we vendor the two modules into the same
repository as bundled sibling addons. Customers who install through the
apps.odoo.com flow receive all three addons in one package; customers
who already have OCA's official versions on their addons path will see
those used (Odoo resolves the first match on the addons path).

The fuller rationale, alternatives considered, and the licence
implications are documented in
[`docs/adr/012-vendor-oca-dependencies.md`](docs/adr/012-vendor-oca-dependencies.md).

## Bundled addons

### `auditlog/`

- **Origin**: https://github.com/OCA/server-tools/tree/19.0/auditlog
- **Version vendored**: `19.0.1.0.1`
- **Copyright**: © 2015 ABF OSIELL <https://osiell.com> · © Odoo Community Association (OCA)
- **Licence**: AGPL-3.0 or later (LICENSE file lives in the vendored folder)
- **Modifications**: **none**. The directory is a verbatim copy of the
  upstream source as of the date this repository was last synced. If
  upstream changes need to be merged in, the entire folder will be
  replaced rather than diff-patched.

### `base_user_role/`

- **Origin**: https://github.com/OCA/server-backend/tree/19.0/base_user_role
- **Version vendored**: `19.0.1.0.2`
- **Copyright**: © 2014 ABF OSIELL <https://osiell.com> · © Odoo Community Association (OCA) · © Tecnativa · © Camptocamp
- **Licence**: LGPL-3.0 or later (LICENSE file lives in the vendored folder)
- **Modifications**: **none**. Same vendoring policy as `auditlog/`.

## Licence compatibility

- `pan_mcp_pro_governance` is **AGPL-3.0-or-later**.
- `auditlog` is **AGPL-3.0-or-later** — the same licence, no friction.
- `base_user_role` is **LGPL-3.0-or-later** — LGPL is compatible with AGPL
  when combined; the combined work as a whole is governed by AGPL-3.

## How to refresh the bundled copies

When OCA releases new versions of either module:

```bash
# from the repo root
rm -rf auditlog/ base_user_role/
git clone --depth 1 --branch 19.0 https://github.com/OCA/server-tools.git /tmp/oca-st
git clone --depth 1 --branch 19.0 https://github.com/OCA/server-backend.git /tmp/oca-sb
cp -R /tmp/oca-st/auditlog ./auditlog
cp -R /tmp/oca-sb/base_user_role ./base_user_role
rm -rf /tmp/oca-st /tmp/oca-sb
# update NOTICE.md with the new versions; commit
```

The vendored copies must never be edited locally. If a fix is needed,
file an issue or PR with OCA and roll the upstream change forward when
it is merged.

## Contact

For licence questions: <support@pantalytics.com>
For OCA source authority: <https://odoo-community.org>
