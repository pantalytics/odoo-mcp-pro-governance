# ADR-003: Drop v0.1 `audit_log` and `api_call_log` models in v0.2.0

**Status:** Accepted (2026-05-18)

## Context

v0.1 declared two models:

- `mcp.governance.audit.log` — append-only per-record ORM trail.
- `mcp.governance.api.call.log` — append-only per-HTTP-request log, correlated by `x_request_id`.

Neither was populated. No controller, dispatch hook, post-init seed, or external pusher wrote to them. They were schema definitions waiting for a writer.

[ADR-002](002-depend-on-oca-auditlog.md) replaces both with OCA `auditlog` models (`auditlog.log`, `auditlog.log.line`, `auditlog.http.request`, `auditlog.http.session`).

## Decision

Drop both v0.1 models in the v0.2.0 release:

- Delete `models/audit_log.py` and `models/api_call_log.py`.
- Delete the corresponding views, ACL rows, tests, and menu entries.
- Add `migrations/19.0.0.2.0/pre-migration.py` that drops the two tables on upgrade (`mcp_governance_audit_log`, `mcp_governance_api_call_log`).
- The migration logs row counts before dropping, but does not preserve data (the tables were empty on every real install).

## Consequences

**Positive**
- Less dead schema. Single source of truth (OCA auditlog) for "what happened."
- No risk of users confusing the empty in-house tables with the OCA-populated ones.
- Migration is safe: tables are guaranteed empty in any real v0.1 deployment.

**Negative**
- One-way migration: customers on v0.1 who somehow populated those tables (custom scripts) would lose data. Mitigation: the migration logs row counts > 0 as a warning rather than silently dropping.
- Foreign keys from third-party modules to `mcp.governance.*` would break, but no such integrations exist (this is a freshly published v0.1 with no ecosystem).
- v0.1's `x_request_id` correlation pattern is abandoned. Future code that needs request → ORM-action linkage uses OCA's `auditlog.log.http_request_id` instead.
