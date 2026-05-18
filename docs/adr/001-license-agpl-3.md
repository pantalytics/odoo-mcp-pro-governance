# ADR-001: License switch LGPL-3 → AGPL-3 in v0.2.0

**Status:** Accepted (2026-05-18)

## Context

v0.1 of this addon was published under **LGPL-3**. In v0.2.0 we add a hard dependency on OCA `auditlog`, which is licensed **AGPL-3**. AGPL-3 is viral for derivative and network-accessed works — linking against it forces our addon to adopt a compatible license.

We also evaluated forking OCA `auditlog` (would inherit AGPL-3 anyway) and rolling our own audit pipeline (~150 LOC, would keep LGPL-3). See [research/08_api_call_logging_options.md](../research/08_api_call_logging_options.md).

## Decision

License v0.2.0 onward as **AGPL-3**. Update `LICENSE`, `__manifest__.py`, `README.md`, and Odoo App Store listing accordingly.

## Consequences

**Positive**
- Lets us depend on OCA `auditlog` and any future OCA modules under AGPL-3 without licensing friction.
- AGPL-3 is well understood and accepted by the Odoo community; OCA modules are all AGPL-3.
- For a free €0 App Store addon with no proprietary IP to protect, the AGPL "must share modifications" obligation costs us nothing.

**Negative**
- One-way change: we cannot return to LGPL-3 without ripping out the OCA dependency.
- If a future commercial product wants to embed this addon in a closed-source stack, AGPL-3 blocks that. We would need to maintain a re-licensed fork or factor the proprietary bits into a separate module.
- Customers integrating non-OSS code with this addon need to understand AGPL obligations apply when the system is network-accessible (which Odoo always is).
