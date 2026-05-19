# Screenshots to add for v0.4 listing

The v0.4 rewrite of `index.html` dropped three screenshots that
referenced features no longer in the module:

- `first_screenshot.png` — Agent Identities list view (model parked
  in v0.4, hidden behind `base.group_no_one`).
- `audit_log_screenshot.png` — the v0.1 `mcp.governance.audit.log`
  model (dropped in v0.2 in favour of OCA `auditlog`).
- `api_call_log_screenshot.png` — the v0.1
  `mcp.governance.api.call.log` model (dropped in v0.2).

To bring the listing up to product reality, add the following new
screenshots before the next App Store submission. Capture on a clean
demo database with realistic but anonymised data.

## 1. `apikey_wizard.png`

Settings → Users → admin → Account Security → click "Add API Key" →
confirm password. Show the wizard with:
- "Name your key" + a populated description (e.g. "Cron Sync Bot")
- "Role (optional)" dropdown open, showing 2-3 roles to choose from
- "Give a duration for the key's validity"
- Generate / Cancel buttons

This is the centrepiece of the listing — it shows the operator
making a scoping choice at the point of key creation.

## 2. `apikey_list.png`

Settings → Users → admin → Account Security → API Keys block (or the
new MCP Pro → API Keys top-level menu). Show 3-4 keys with mixed
role / state / last-used. Make sure at least one shows:
- Role: <some role name>
- State: Active
- Last used: <recent timestamp>
- Use count: <three-digit number>

Demonstrates the per-key observability.

## 3. `audit_log.png`

MCP Pro → Audit Log (= OCA `auditlog.http.request` list). Show
~10 rows of recent inbound calls with method, path, user, timestamp.
At least one row should expand to show the linked `auditlog.log`
entries with field-level diff.

## Constraints

- PNG. Width 1200-1600px is fine; the App Store viewer scales them.
- Anonymise any customer names / emails.
- Avoid showing the entire Odoo top menu — crop to the relevant pane
  so the screenshot reads at thumbnail size.
- Keep the colour palette consistent (default Odoo theme is fine).

## After capturing

1. Drop the three files into this directory.
2. Update `index.html` to reference them in the appropriate sections
   (currently the "Scoped API keys", "Audit log" and possibly a new
   "Lifecycle at a glance" block are text-only).
3. Delete this `SCREENSHOTS_TODO.md` file in the same commit.
