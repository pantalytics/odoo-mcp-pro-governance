# Changelog

All notable changes to this module are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/).

## [19.0.1.20.1] - 2026-07-06

### Fixed
- **API-key wizard crashed on non-English instances.** The Role dropdown
  inherit anchored on the parent heading's *text*
  (`//h3[contains(., 'Give a duration')]`). Odoo applies view inheritance
  against the translated arch, so on a Dutch (or any non-English) instance
  the literal English text was absent and combining the
  `res.users.apikeys.description` view raised
  `Element '<xpath .../>' cannot be found in the parent view` — the
  "New API Key" wizard would not open at all. The xpath now anchors
  structurally on the heading preceding the `duration` field
  (`//field[@name='duration']/preceding-sibling::h3[1]`), which is
  language-independent and robust to other modules adding headings.
  Added a regression test that combines the wizard view under a translated
  `nl_NL` heading.

## [19.0.1.3.0] - 2026-05-20

### Added
- **Link audit log entries to the API key that produced them.**
  `auditlog.http.request` now has an `x_api_key_id` field, filled at
  request-ingest time from `request.session["x_mcp_api_key_id"]` (set
  by `pan_mcp_pro_governance`'s `res.users.apikeys` auth hook). A
  stored related field on `auditlog.log` exposes the key on every log
  row, so operators can answer "which API key made this change?"
  directly from the Logs list / form / search view. Empty for
  cookie-based browser sessions.

## [19.0.1.2.0] - 2026-05-20

### Changed
- **Rename bundled OCA modules to `pan_mcp_auditlog` and
  `pan_mcp_user_role`.** apps.odoo.com refuses to accept uploads under
  the canonical OCA names `auditlog` and `base_user_role` because they
  are already registered there for older Odoo series (17.0, 18.0) by
  OCA themselves, and OCA has not published a 19.0 version. The rename
  lets us publish the bundle without name conflicts. Python model
  names (`auditlog.rule`, `res.users.role`, …) are unchanged — only
  the module folder + manifest `name` field move.
- `pan_mcp_pro_governance/__manifest__.py` `depends` now lists
  `pan_mcp_auditlog` and `pan_mcp_user_role`.
- XML records inside the renamed bundles that referenced their own
  records with full module qualification (`ref('auditlog.x')` /
  `ref('base_user_role.x')`) updated to the new module prefix.
- `pan_mcp_pro_governance` XML group + action refs updated to the new
  module prefix.

### Added
- ADR-013: rename bundled OCA modules. Documents the apps.odoo.com
  name-uniqueness constraint discovered during publish + the
  coexistence trade-off with the OCA originals.

### Notes
- ADR-012 (bundle as sibling addons under OCA's original names)
  superseded by ADR-013.
- Customers already running OCA's official `auditlog` or
  `base_user_role` cannot install the Pantalytics bundle in the same
  database — see [`NOTICE.md`](NOTICE.md) for the two ways to
  resolve. Fresh installs ("Deploy on Odoo.sh") are unaffected.
- Listing version stamp bumped to v1.2.0.

## [19.0.1.0.0] - 2026-05-20

### Changed
- **v1.0 milestone.** Stable release of the scoped-API-keys + audit-log
  bundle. No code changes from v0.5.0 — version bump only, marking the
  module as production-ready for apps.odoo.com.
- Listing version stamp bumped to v1.0.0.

## [19.0.0.5.0] - 2026-05-20

### Changed
- **Vendor OCA dependencies into the repo.** OCA `auditlog`
  (`19.0.1.0.1`) and OCA `base_user_role` (`19.0.1.0.2`) are now
  bundled as sibling addons at the repository root. Customers
  installing via apps.odoo.com get all three modules in a single
  upload; customers who already have the OCA originals on their
  addons path can continue using those.
- `auditlog` and `base_user_role` restored to `__manifest__.py`
  `depends`. Runtime functionality returns to what v0.4.0 shipped.
- Listing version stamp bumped to v0.5.0.

### Added
- `NOTICE.md` at repo root — explicit attribution, origin URLs,
  copyright holders, licences, and a "how to refresh" procedure for
  the vendored folders.
- ADR-012: vendor OCA dependencies into the repo. Documents the
  apps.odoo.com publisher-portal behaviour that forced this choice,
  alternatives considered, and the operational policy that vendored
  folders are never edited locally.

### Notes
- Vendored folders are verbatim copies of the upstream OCA sources.
  No modifications. Refreshing on a new OCA release is wholesale
  folder replacement, never diff-patching.
- License compatibility: `pan_mcp_pro_governance` AGPL-3 +
  `auditlog` AGPL-3 + `base_user_role` LGPL-3. Combined distribution
  remains AGPL-3.

## [19.0.0.4.3] - 2026-05-20

### Changed
- **Diagnostic, step 2**: also removed `base_user_role` from `depends`.
  Step 1 (v0.4.2, dropping just `auditlog`) caused the publisher
  portal to shift its warning to `base_user_role` rather than accept
  the update — confirming that any single OCA dep blocks the
  listing refresh. With both removed, the manifest now has zero
  OCA dependencies; if the live page picks up the v0.4.3 stamp
  this revision, the hypothesis is fully proven and we move on to
  the vendor-in-repo plan.
- Version stamp updated in `static/description/index.html`.

## [19.0.0.4.2] - 2026-05-20

### Changed
- **Diagnostic**: removed `auditlog` from `depends` to test the hypothesis
  that apps.odoo.com's rescan is silently rejecting the v0.4 listing
  due to the unmet OCA dependency. Runtime is intentionally broken in
  this revision; expected to be restored to v0.4.x once the publisher
  portal accepts the updated listing.
- Added a visible version stamp at the bottom of `static/description
  /index.html` so the live apps.odoo.com page can be inspected for
  which revision is currently published.

## [19.0.0.4.1] - 2026-05-20

### Changed
- Version bump only. Triggers an apps.odoo.com rescan so the v0.4
  listing copy (rewritten manifest description, new screenshots,
  broader positioning) replaces the v0.1 content currently shown
  on the live store page.

## [19.0.0.4.0] - 2026-05-19

### Security

- Close the `/jsonrpc` narrowing bypass. The legacy endpoint runs
  `dispatch_rpc()` inside `borrow_request()` which pops the request
  from the local stack — writes to `request.session` during
  `_check_credentials` did not survive to subsequent ACL checks, so a
  narrow-role key got full user permissions through this route. Fixed
  by also stashing the matched role on a thread-local.
- Thread-local is cleared at the start of every request via
  `ir.http._dispatch`, preventing leakage to UI sessions on the same
  worker thread.

### Changed

- Narrow at the source: rewrote the narrowing layer so
  `res.users._get_group_ids` and `_compute_all_group_ids` are the
  single point of truth. Every Odoo path that asks "what groups does
  this user have?" now gets the role's groups when an API-key role is
  in scope. Removes the previous per-check overrides on `_has_group`
  and `ir.model.access.check`.
- Cache-bypass on `ir.model.access._get_allowed_models` (parent's
  ormcache key has no role component) when a role is active.
- `ir.rule._compute_domain` cache made role-aware by extending
  `_compute_domain_keys` with `_mcp_api_key_role_id`, so each (uid,
  role) gets a distinct cache entry.
- Manifest description rewritten to lead with scoped API keys as the
  primary value proposition. Agent identity moved to roadmap.
- `mcp.governance.agent.identity` menu hidden behind
  `base.group_no_one`; model and views stay in the codebase for
  developer-mode access and future surfacing in v0.5.

### Added

- ADR-011: one role per API key (Many2one), not many — least-privilege
  over OCA-style stacking.

## [19.0.0.3.0] - 2026-05-19

### Added

- Depend on OCA `base_user_role` 19.0 (`server-backend` repo).
- `res.users.apikeys` gains `x_role_id` (Many2one →
  `res.users.role`), `x_state` (active / suspended / revoked),
  `x_last_used`, `x_use_count`.
- API key creation wizard adds an optional Role dropdown, filtered to
  the roles assigned to the current user. Wizard's `make_key` stamps
  the role onto the freshly generated key row.
- `res.users.apikeys._check_credentials` override stashes the matched
  key id and (optional) role id on the request session.
- `res.users._has_group` override narrows menu/view-level group checks
  to the role's groups when an API-key role is in scope.

### Changed

- "API Key Ready" modal warning rewritten — "provides full access to
  your user account" was misleading once roles entered the picture.
  New text points at the role as the actual security boundary.
- API key wizard layout fixed: Role section now sits between the Name
  and Duration sections (xpath was off by one element).
- Role binding is *optional*: keys without a role behave like
  standard Odoo keys (full user permissions). This matches OCA
  `base_user_role`'s own posture for users.

### Documented

- ADR-005: Odoo per-user billing as a hard architectural constraint.
- ADR-006: per-API-key attribution via patched auth flow.
- ADR-007: `base_user_role` integration (superseded by 010 — promoted
  from optional to required).
- ADR-008: context-tagging fallback (superseded by 010).
- ADR-009: parallel scope system (superseded by 010 — pivoted to
  composing with OCA roles instead of inventing scope strings).
- ADR-010: API key bound to a single OCA user role.

## [19.0.0.2.0] - 2026-05-18

### Changed

- **License switch LGPL-3 → AGPL-3** (ADR-001). Required by the
  dependency on OCA `auditlog` (AGPL-3).
- Depend on OCA `auditlog` 19.0 (ADR-002). Our addon becomes a thin
  configuration layer + AI-agent UI skin on top.

### Removed

- `mcp.governance.audit.log` and `mcp.governance.api.call.log` models
  from v0.1 — never populated in production (ADR-003). Migration in
  `migrations/19.0.0.2.0/pre-migration.py` drops the empty tables on
  upgrade.

### Added

- `post_init_hook` (`hooks.py`) seeds draft `auditlog.rule` records
  for sale.order, res.partner, account.move, crm.lead,
  product.template, stock.picking — conditional on each model's
  owning module being installed.
- Smart-button "API Calls" on the agent identity form opens a
  filtered `auditlog.http.request` view for that agent's user.
- `group_mcp_governance_user` and `group_mcp_governance_manager` now
  imply `auditlog.group_auditlog_user` / `_manager` respectively.

### Verified

- End-to-end on production `pantalytics.odoo.com`: MCP call →
  `auditlog.log` row with linked `http_request_id` and `http_session_id`.

## [19.0.1.0.2] - 2026-05-08

### Changed
- Removed pricing tiers from the App Store listing and manifest
  description. The Odoo App Store frame is "free addon" - users
  discovering the SaaS register on pantalytics.com themselves.

## [19.0.1.0.1] - 2026-05-08

### Changed
- App Store listing flipped to lead with the AI-connector value
  proposition (Claude / ChatGPT / Gemini / Copilot / Mistral) and the
  hosted MCP Pro server, with governance positioned as the differentiator
  in the second half. Adds demo GIF, AI tool logos, and the three
  customer testimonials from the SaaS landing page.
- Manifest `summary` and `description` rewritten to match the funnel.
- Pre-commit `check-added-large-files` raised to 5MB to fit the demo GIF.

## [19.0.1.0.0] - 2026-05-08

### Security
- Audit and API call logs: removed `perm_create` from the module's
  Manager group. Rows can now only be inserted by `base.group_system`
  (the MCP server's technical user). Closes a hole where a UI Manager
  could inject false audit rows while `write()`/`unlink()` were already
  blocked.
- Pre-commit: added `gitleaks` secrets scan.

### Changed
- App Store description: removed external GitHub link to comply with
  reviewer guidelines (only `mailto:` and YouTube canonical anchors
  allowed).
- Group comments and README clarified: User/Manager are read-only on
  audit and API call logs; no record rules yet, both see all rows.

### Added
- Initial repo scaffold under module directory `pan_mcp_pro_governance/`
  (matches Pantalytics `pan_*` naming).
- `mcp.governance.agent.identity` model: AI agent as a first-class Odoo
  identity, distinct from `res.users`.
- `mcp.governance.audit.log` append-only log with agent identity link.
- Security groups `group_mcp_governance_user` and
  `group_mcp_governance_manager`.
- Top-level "Governance" menu.
