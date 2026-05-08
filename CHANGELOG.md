# Changelog

All notable changes to this module are documented here. Format loosely
follows [Keep a Changelog](https://keepachangelog.com/).

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
