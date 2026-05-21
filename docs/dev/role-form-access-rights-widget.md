# Role form: reuse Odoo's Access Rights widget

**Status**: implemented in v19.0.1.7.1
**Decided**: 2026-05-21
**Affects**: `pan_mcp_pro_governance` (new view inherit + one field
override on res.users.role), `pan_mcp_user_role` (no change)

## Problem

The OCA `base_user_role` form (vendored as `pan_mcp_user_role`) renders
the role's groups as a flat `many2many_tags` dropdown. That dropdown
mixes mutually-exclusive selection groups (e.g. `Sales / User: All
Documents` vs `Sales / User: Own Documents Only`) with additive groups
(e.g. `Project / User`), with no visible distinction. A user can pick
both Sales levels and Odoo silently picks one — confusing.

The standard Odoo `res.users` form solves this with the "Access Rights"
tab: groups grouped by category, with a dropdown per privilege and
checkboxes for extras. We want that on the role form too — same mental
model whether you're scoping a user or a role.

## Why the widget can be reused as-is

The widget's own docstring says:

> This widget is only used for the 'group_ids' field of the 'res.users'
> form view or the 'implied_ids' field of the 'res.groups' form view,
> in order to vizualize and configure access rights.

Source:
[`odoo/addons/web/static/src/webclient/res_user_group_ids_field/res_user_group_ids_field.js`](../../../odoo-source-code/odoo-19.0.post20260519/odoo/addons/web/static/src/webclient/res_user_group_ids_field/res_user_group_ids_field.js#L13-L17)

`res.users.role` (OCA) has `_inherits = {"res.groups": "group_id"}`
([role.py:14](../../pan_mcp_user_role/models/role.py#L14)), so:

- `implied_ids` is exposed on the role record (inherited M2M to res.groups)
- `view_group_hierarchy` (computed JSON field on res.groups,
  [res_groups.py:37](../../../odoo-source-code/odoo-19.0.post20260519/odoo/addons/base/models/res_groups.py#L37))
  is exposed too

The widget reads `this.props.name` (dynamic field name) and writes back
via `this.props.record.update`, so it is not res.users-hardcoded
beyond the docstring example.

## Change made

**1. View inherit**
[`pan_mcp_pro_governance/views/mcp_governance_role_views.xml`](../../pan_mcp_pro_governance/views/mcp_governance_role_views.xml)
targets `pan_mcp_user_role.view_res_users_role_form` and switches the
widget on `implied_ids` from `many2many_tags` to `res_user_group_ids`.

**2. Field override on `res.users.role`** (the small Python piece I
initially hoped we could avoid)
[`pan_mcp_pro_governance/models/res_users_role.py`](../../pan_mcp_pro_governance/models/res_users_role.py)
redeclares `view_group_hierarchy` with a local compute. Reason: on a
*new* role record the inherited compute on res.groups does not run
yet (no associated group_id exists until save), so the widget crashed
on `Object.values(undefined)`. The local compute always returns the
global hierarchy, which is correct for both new and existing roles.

Discovered by running, not from the source. The widget docstring did
not warn about this; the OwlError surfaced on first navigation to
`/odoo/user-role/new`.

## Verified by running (2026-05-21)

- Form load on **new** role: hierarchy renders, categories
  (Master Data, MCP Pro, Marketing) appear with dropdowns. ✓
- Selecting `MCP Pro: Administrator`, saving: persists. ✓
- Reload existing role: still shows `MCP Pro: Administrator`,
  Associated group field populated, no console errors. ✓
- OCA-specific surface (stat buttons "Access Rights" / "Record Rules"
  counters, Users tab) keeps working. ✓

Screenshots in repo root: `role-form-new-after-fix.png`,
`role-form-mcp-admin-selected.png`, `role-form-existing-after-fix.png`.

## Odoo-upgrade checklist

The widget is registered under the field-widget name
`res_user_group_ids` and depends on:

- `res.groups._get_view_group_hierarchy()` — JSON shape (categories,
  privileges, groups)
- `res.groups.privilege` model — the new Odoo 19 first-class privilege
  concept
- `res.groups.implied_ids` (M2M self-relation) — the field the widget
  writes to

On each Odoo major upgrade we **must** verify that:

- the widget name `res_user_group_ids` still exists in the registry
- `_get_view_group_hierarchy()` still returns the same shape (or our
  view-inherit still works against the new shape)
- the privilege model has not been renamed or restructured

If any of these change, the role form falls back to the OCA default
`many2many_tags` rendering — degraded UX but not broken — and we
schedule the patch.
