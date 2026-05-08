# Research — `odoo-mcp-pro-governance`

Deep research conducted before a single line of module code is considered
final. Each memo stands alone with primary sources; the synthesis ties
them together into concrete design decisions for the module.

## Memos

| # | File | Axis |
|---|---|---|
| 01 | [microsoft_reference_architecture.md](01_microsoft_reference_architecture.md) | Microsoft as the reference mental model: Entra Agent ID, Purview, Defender, Copilot Studio, Security Copilot |
| 02 | [standards_and_literature.md](02_standards_and_literature.md) | NIST AI RMF, ISO/IEC 42001, EU AI Act, OWASP LLM Top 10, CSA AI Controls, MITRE ATLAS |
| 03 | [odoo_current_state.md](03_odoo_current_state.md) | What Odoo (Community + Enterprise + OCA) already has for auth, ACLs, audit, API keys; gaps across versions 17/18/19 |
| 04 | [mcp_ecosystem.md](04_mcp_ecosystem.md) | MCP spec auth, OAuth 2.1 + resource indicators, fine-grained authz (Cerbos/OpenFGA/Permit.io), audit patterns across MCP servers |
| 05 | [how_ai_breaks_controls.md](05_how_ai_breaks_controls.md) | Speed, prompt injection, SoD collapse, data exfil, tool chaining, real incidents |
| 06 | [competitive_landscape.md](06_competitive_landscape.md) | SAP Joule, Oracle AI Agent Studio, Workday, NetSuite, and what exists on the Odoo app store today |

## Synthesis

- [synthesis.md](synthesis.md) — concrete design decisions, data model, roadmap anchored to the **2026-08-02 EU AI Act deadline**, decision log (14 commitments), and the 8 questions reserved for the first architecture spike.

## Method

- Each memo is the result of a dedicated research pass; agents are
  instructed to cite primary sources (vendor docs, normative standards,
  peer-reviewed papers, official specs) over secondary commentary.
- Direct quotes are used where the wording itself matters (definitions,
  regulatory text, API surface).
- "Open questions for synthesis" at the end of each memo is the
  hand-off into the synthesis document.
