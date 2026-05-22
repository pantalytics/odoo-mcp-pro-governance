# Feedback Loops

Eén bron voor "hoe weet ik dat mijn wijziging goed is?" Van snelste loop (seconden) naar traagste (minuten). Pak altijd de snelste die je antwoord geeft.

## De ladder

| # | Loop | Wat het beantwoordt | Tijd | Hoe |
|---|---|---|---|---|
| 1 | Pre-commit (ruff + format) | Style + simpele bugs | <2s | `make lint` of automatisch bij commit |
| 2 | `--dev=all` reload | View XML / Python wijziging zichtbaar? | <5s | Browser refresh; geen restart nodig |
| 3 | Eén test | Specifiek model/method werkt? | ~15s | `make test-one TAG=:TestClass.test_method` |
| 4 | Module-tests | Niets regressed? | ~90s | `make test` |
| 5 | UI-feedback skill | Klopt deze view met de design-filosofie? | ~30s | `/ui-feedback` (zie skill in `~/.claude/skills/ui-feedback`) |
| 6 | Tour-tests (HttpCase) | UI-flow werkt end-to-end? | ~60s | `make test-one TAG=:TestGovernanceSmokeTour` |
| 7 | Fresh-DB install | Survives een App Store reviewer? | ~3 min | `make test` (begint altijd met fresh DB) |
| 8 | CI op PR | Werkt het ook in een schone GitHub-omgeving? | ~6 min | `git push` |

## Welke loop voor welke wijziging?

| Je hebt veranderd... | Pak loop |
|---|---|
| Pythoncode in een model | 3 → 4 |
| View XML | 2 (refresh) → 6 (tour) |
| Manifest / nieuwe field / ACL / data XML | `make upgrade`, dan 4 |
| OWL JS / SCSS | Hard refresh `/web?debug=assets`, dan 6 |
| Menu of view-structuur | 5 (skill) → 4 (Python contract test) |
| Hooks (`hooks.py`, migrations) | 4 — gebruikt fresh DB |
| Iets aan listing HTML in `static/description/` | 8 (CI heeft een listing-validator) |
| ADR / docs / README | Niets — alleen `make lint` voor markdown-formatting |

## Inner loop in detail

### Loop 1 — pre-commit

```bash
make lint                 # Alles
pre-commit run ruff       # Alleen ruff
```

Ruff doet formatting + lints. Mislukt iets: lees de regel, fix, en commit opnieuw. **Niet --no-verify gebruiken.**

### Loop 3 — één test

Test-tags volgen `:Klasse.methode`. Voorbeeld:

```bash
make test-one TAG=:TestApiKeys.test_role_narrowing
```

De test draait op een verse `test_one_<timestamp>` DB. De daadwerkelijke dev-DB blijft draaien voor browser-iteratie.

### Loop 4 — module-tests (de canonical loop)

```bash
make test
```

Wat dit precies doet — en waarom dat zo ontworpen is:

1. Maakt een verse DB `test_<timestamp>`.
2. Installeert de module daarin (vangt install-time fouten — dit is de #1 App Store takedown trigger).
3. Draait alle tests met tag `/pan_mcp_pro_governance`.
4. Dropt de DB. De dev-DB blijft ongemoeid.

Als 4 groen is op je laptop is de kans dat CI groen wordt >95%.

### Loop 5 — UI-feedback skill

`/ui-feedback` opent een Playwright-sessie tegen de lokale Odoo (`localhost:8069`, db `dev`). Het rapporteert:

- Hoeveel top-level app-tegels deze module aanmaakt (moet `1` zijn).
- Welke kleuren op de geselecteerde view voorkomen (waarschuwing als brand-accent `#9b99ff` lekt in de Odoo-UI).
- Of empty-state placeholders aanwezig zijn op de lijst-views.
- Of forms een statusbar hebben en alleen lifecycle-knoppen tonen die bij de huidige state horen.

Run het na elke wijziging aan views/menus. Zie [design.md](design.md) voor wat de regels zijn.

### Loop 6 — tour-tests

Wat zijn tours? Odoo's eigen UI-test-framework. JS-bestanden in `static/src/js/tours/` zijn de stappen, Python `HttpCase` in `tests/test_*_tour.py` triggert ze. De assets worden geladen via de `web.assets_tests` bundle in het manifest.

```bash
make test-one TAG=:TestGovernanceSmokeTour
```

Een tour faalt als een selector niet gevonden wordt binnen de timeout. Veel voorkomende oorzaken:

- Menu xmlid is gewijzigd zonder de tour bij te werken.
- Een knop is nu pas zichtbaar in een bepaalde state — voeg een tussenstap toe die die state bereikt.
- Asset-bundle cache. Hard refresh, of `make restart`.

### Loop 7/8 — CI

De `test` job in `.github/workflows/ci.yml` doet hetzelfde als loop 4 maar:

- In een schone Ubuntu container.
- Tegen Postgres 16.
- Zonder lokale filestore.
- Met Odoo 19 Community (geen Enterprise — dus geen Enterprise-only paden testen!).
- Chromium wordt apt-installed zodat HttpCase tours niet stilletjes overgeslagen worden.

Daarnaast draaien er twee aparte gates:

- **Fresh-install gate** — installeert het module op een lege DB zonder demo-data en zonder `--test-enable`. Dat is letterlijk wat de Odoo App Store reviewer doet. Faalt deze stap → listing-rejection bij submit.
- **Manifest version bump check** — alleen op PRs. Faalt wanneer code/views/csv in `pan_mcp_pro_governance/` veranderden zonder dat `__manifest__.py` zijn `version` bumpte. Documentatie en tests vallen erbuiten, lifecycle van OCA `auditlog`-conventies blijft intact.

Faalt CI maar werkt het lokaal: meestal Enterprise-vs-Community drift of een lokaal cached asset.

## UI-feedback skill — wat zit erin?

`/ui-feedback` (in `~/.claude/skills/ui-feedback/`) draait via Playwright MCP tegen de lokale Odoo en checkt de vijf regels uit [design.md](design.md):

1. Eén top-level app van deze module (geen tweede).
2. App-naam matcht `__manifest__.py`.
3. Empty-state placeholders aanwezig op lijsten zonder records.
4. Statusbar op lifecycle-forms.
5. Geen brand-accent `#9b99ff` in de Odoo UI.

Output is een markdown-rapport. De skill *rapporteert* — fixt niets zelf. Wijzigingen aan de UI doe je dan in een aparte iteratie.

## Snelle checks voor zelfvertrouwen

Voor je een PR opent, draai in deze volgorde:

```bash
make lint                                       # ~2s
make test-one TAG=:TestApiKeys                  # ~15s
make test                                       # ~90s — fresh DB install gate
# UI-wijziging?
/ui-feedback                                    # ~30s
make test-one TAG=:TestGovernanceSmokeTour      # ~60s
```

Alles groen? Push. CI is dan slechts een sanity-check, geen ontdekking.
