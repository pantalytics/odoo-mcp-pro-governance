# End-to-end flow test — MCP Pro governance addon

**Goal**: walk through the full user journey on a clean install with
realistic apps (Sales, CRM, Project) and verify each step works both
**functionally** (the action does what it says) and **UX-wise** (a
new user can find their way).

**Test environment**: dev DB, http://localhost:8069, admin/admin.
Module at v19.0.1.7.1. Apps installed: sale_management, crm, project.

## Step 1 — Landing on the MCP Pro menu

- [x] Top-level "MCP Pro" menu shows up in the nav bar for admin
- [x] Click it → lands on "Get Started" page with 5 numbered steps
- [x] Empty-state copy reads well, no Lorem Ipsum, no broken links
- [x] Two CTAs (Sign up, Open MCP Pro) point to actionable destinations
- [x] Agent Identities menu correctly gated behind `base.group_no_one`
      (visible to admin in debug mode only — not a leak)
- [ ] **FINDING — flow order**: current onboarding suggests key first,
      role later (and marks role as optional). For a governance tool
      this lures users into making an unscoped key. Proposed reorder:
      role first → key linked to that role at creation time → "review
      audit log" as a follow-up rather than an optional afterthought.
- [ ] **FINDING — App Store listing**: separate from onboarding, the
      listing copy should make clear the hosted SaaS works without
      installing this addon. Out of scope for this test pass.
- [ ] **FINDING — "Pantalytics" in step 1 copy**: acceptable in-app,
      but watch for App Store reviewer pushback on external branding.

**Files in scope**: [views/mcp_governance_onboarding_views.xml](../../pan_mcp_pro_governance/views/mcp_governance_onboarding_views.xml),
[views/mcp_governance_menus.xml](../../pan_mcp_pro_governance/views/mcp_governance_menus.xml),
[models/get_started.py](../../pan_mcp_pro_governance/models/get_started.py),
[static/description/index.html](../../pan_mcp_pro_governance/static/description/index.html)

## Step 2 — Assign a role to an existing human user

- [x] Created "Demo Sales Rep" (login: demo_sales) via Settings → Users
- [x] "User Roles" tab is the first tab (OCA inherit) — good UX
- [x] Add a line → autocomplete shows "AI Test Role" → picked
- [x] Save → role row persists with Enabled checked, no from/to dates
- [x] Groups counter went 2 → 4 — role's implied groups attached
- [ ] **FINDING — external-user trap**: a freshly created user without
      manually setting Access Rights is flagged "EXTERNAL USER" (no
      `base.group_user`). The role assignment still works, but for the
      "AI scoping" use case the user must be internal to own API keys.
      Either we document this, or we set `base.group_user` as default
      on the user form (this is Odoo behavior, not ours).

**Files in scope**: [pan_mcp_user_role/views/user.xml](../../pan_mcp_user_role/views/user.xml),
[pan_mcp_user_role/models/user.py](../../pan_mcp_user_role/models/user.py)

## Step 3 — Create a dedicated AI role

- [x] Created "AI Sales Read-Only" via /odoo/user-role/new
- [x] Sales dropdown showed 4 levels: No / User: Own Docs / User: All
      Docs / Administrator — exactly the standard Odoo selection group
- [x] Picked "User: Own Documents Only" (tightest read)
- [x] Save → role id=3, Associated group "AI Sales Read-Only" populated
- [x] Access Rights counter 42, Record Rules counter 15 (reasonable
      narrowing — full admin would be hundreds)
- [x] **Observation — implied groups surface honestly**: Products
      auto-set to "View" because Sales:User implies Products read.
      The widget shows it (greyed-out behaviour) rather than hiding,
      which is the right transparency choice.

## Step 4 — Assign the AI role to admin (key-owner)

- [x] Admin user → User Roles → "AI Sales Read-Only" added
- [x] Save → no errors, Groups counter went 14 → 16 (role's groups
      attached additively)
- [x] Required by `_check_role_belongs_to_user` constraint on
      res.users.apikeys

## Step 5 — Create an API key bound to the AI role

- [x] Security tab → Add API Key → password confirmation → wizard
- [x] Wizard shows 3 sections: Name, Role (optional), Duration
- [x] Role copy is clear: "Pick a role to scope this key down to a
      narrower set of permissions. Leave empty to inherit your user's
      full permissions (the standard Odoo behaviour)."
- [x] Empty-state hint under field: "No role: this key will have the
      same access as your user account."
- [x] Role dropdown filtered to admin's assigned roles only — showed
      only "AI Sales Read-Only" (not "AI Test Role" assigned to Demo
      Sales Rep)
- [x] Pick role → Generate → key revealed once with rewritten warning
      that names the role
- [x] DB confirm: key id=1, x_role_id=3, x_state=active, x_use_count=0
- [ ] **FINDING — default Duration "1 Day"**: standard Odoo default.
      For an always-on AI agent this is too short; the AI's key will
      auto-delete after 24h. Consider an MCP-specific default (e.g.
      "1 year" or "never expire") when the user picks a role —
      keeping the standard default when no role is selected.

## Step 6 — Simulated AI call with the key (narrowing path)

URL pattern in Odoo 19: `/json/2/<model>/<method>` (not `/json/2/<method>`).

- [x] `sale.order/search_count` with bearer = our key → `0` (allowed,
      empty DB)
- [x] `account.move/create` with bearer = our key → **AccessError
      with our custom message naming the role**: "The API key you are
      using is bound to the role 'AI Sales Read-Only', which does not
      allow create on model 'account.move'. To fix: either add the
      required groups to this role in Settings → Users & Companies →
      User Roles, or use an API key bound to a broader role."
- [x] `ir.module.module/search_count` returned `1397` — not a leak,
      this model is intentionally readable by any internal user
      (Apps menu requirement)

**Narrowing is confirmed working on writes** ([models/ir_model_access.py](../../pan_mcp_pro_governance/models/ir_model_access.py)
custom `_make_access_error` rewrite fires correctly).

## Step 7 — Verify audit log contains the call

- [x] Activated the `MCP Pro — Contacts` rule (res.partner) via the
      Audit Rules form → state moved Draft → Confirmed
- [x] Created "Audit Test Customer" via the Contacts UI (admin
      session) — a write/create on res.partner
- [x] Audit Log list shows: `/web/dataset/call_kw/res.partner/web_save`,
      session = Administrator, API Key = empty (UI session)
- [x] Audit Log detail (two-column layout from commit 1ed985a) shows
      HTTP REQUEST fields + correlated LOGS rows (create + write on
      "Audit Test Customer")
- [ ] **FINDING — nav-bar context lost**: opening the audit log via a
      deep link puts the user in a generic app shell (top nav showed
      "Contacts" because of the action breadcrumb). Should remain
      under the "MCP Pro" app. Check the action definition.
- [ ] **FINDING — "New" button on the audit log list**: audit logs
      should be read-only at the UI level. A user accidentally
      clicking New would either hit a permission error or create
      a manual orphan entry. Remove the create option from the list
      view.
- [ ] **FINDING — seeding only fires at install time**: hooks.py
      seeds rules for sale.order, account.move, crm.lead, etc.
      *only if those modules are already installed*. Since we
      installed Sales/CRM later, no rules were seeded for them.
      Operators have to manually create rules for each AI-target
      model installed after this addon. Consider re-seeding on
      module install events (`ir.module.module` subscribe), or
      surfacing a "Seed missing rules" button on the rules list.

## Step 8 — Suspend the key (fail-closed test)

Tested via SQL toggles + curl, matrix:

| `x_state` | HTTP status | Body |
|---|---|---|
| `active` | 200 | `0` (sale.order/search_count) |
| `suspended` | 401 | `{"name": "Unauthorized", "message": "Invalid apikey"}` |
| `revoked` | 401 | `{"name": "Unauthorized", "message": "Invalid apikey"}` |

- [x] Suspended and revoked both fail closed — no data leak
- [x] Re-activated key resumes working
- [x] Internal log line "API key id=1 is suspended; denying request"
      fires as expected ([res_users_apikeys.py:152](../../pan_mcp_pro_governance/models/res_users_apikeys.py#L152))

## Step 9 — Edge cases & regressions

- [x] **Fixed during this pass**: pre-existing guard bug
      `_check_minimum_role_manager` was firing during install/test
      DB load and crashing the translate alias. Added an early
      return when `install_mode` is set or registry is not ready
      ([models/res_users_role.py:53-61](../../pan_mcp_pro_governance/models/res_users_role.py#L53-L61)).
- [x] Test suite went from 39 tests + 2 errors to **46 tests, 0
      errors** after the guard fix
- [x] Delete-role-with-users behaviour covered by existing tests
      `test_unlink_unused_role_is_allowed` and
      `test_unlink_role_carrying_sole_admin_settings_group_is_blocked`
      — both green
- [x] No console errors observed during any of the Playwright walks

## Findings summary — separate tracking

1. **Onboarding flow order** (step 1) — current copy implies create
   key first, scope later. Should be: create role → key linked to
   role → review log.
2. **External-user trap** (step 2) — new users without explicit
   Access Rights are flagged external. Out of scope, this is Odoo
   behaviour.
3. **Default API key duration** (step 5) — "1 Day" is the standard
   Odoo default; consider longer default when a role is selected.
4. **Audit log nav-context** (step 7) — deep link drops out of the
   MCP Pro app shell.
5. **Audit log create button** (step 7) — should be read-only.
6. **Audit rule seeding gap** (step 7) — `post_init_hook` only
   seeds for installed modules; doesn't catch up when sale/crm/etc
   are installed after this addon.
7. **App Store listing copy** — should clarify hosted SaaS works
   without installing this addon. Out of scope for this test pass.
