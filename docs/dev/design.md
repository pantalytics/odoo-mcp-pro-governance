# Design — pan_mcp_pro_governance

Dit is het bindende UI-anker voor deze module. Niet de hele Pantalytics-stijlgids — alleen de regels die we hier in Odoo kúnnen afdwingen, plus de "do/don't"-lijst waar ik (Claude) of een nieuwe ontwikkelaar op valt.

De volledige merkfilosofie staat op [brand.pantalytics.com/en/design-philosophy](https://brand.pantalytics.com/en/design-philosophy). Bij twijfel: dat is leidend.

## De vijf principes (uit brand.pantalytics.com)

1. **Progressive disclosure** — Toon alleen wat nu nodig is. Detail komt op aanvraag.
2. **Simplicity first** — Elk element verdient zijn plek. Weghalen zonder verlies = weghalen.
3. **Odoo-native where possible** — Odoo conventies respecteren. Geen eigen CSS waar standaard-widgets volstaan.
4. **Accessible by default** — WCAG AA is het minimum.
5. **Content over chrome** — UI dient de inhoud, niet andersom.

## Wat dat hier concreet betekent

### Menu-structuur (progressive disclosure)

- **Eén top-level app**: "MCP Pro". Geen tweede.
- Dagelijks gebruik direct onder de app: Agent Identities, API Call Log.
- Beheerdersdingen onder **Configuration**. Niet zichtbaar voor de gewone gebruiker (`group_mcp_governance_manager`).
- Verifieerbaar via test (zie [FEEDBACK.md](FEEDBACK.md) — UI-contract tests).

```
MCP Pro
├── Agent Identities        ← dagelijks
├── API Call Log            ← dagelijks
└── Configuration           ← manager-only
    └── Audit Rules
```

### Empty states

- Gebruik de standaard `.o_view_nocontent_smiling_face` placeholder (Odoo-native).
- Tekst is een korte zin in de vorm "Hier komen X te staan zodra Y". Geen jargon.
- **Niet** vullen met "Geen records gevonden" — dat is taal van het systeem, niet van de gebruiker.

### Lijsten

- Default sortering: meest recent eerst (`create_date desc` of vergelijkbaar).
- Standaard zichtbare kolommen: hooguit 5. Detail klap je open via klik op de rij (= progressive disclosure).
- Status-velden krijgen een gekleurde decorator (`decoration-success`, `decoration-warning`, `decoration-danger`) — kleur alleen voor status, niet voor versiering.

### Forms

- Boven aan altijd de naam + state-badge (de drie-vier-status flow als statusbar, niet als selectie-veld).
- Lifecycle-acties als knoppen in de header, alleen zichtbaar in de juiste state. Geen knoppen die niets doen.
- Smart buttons rechtsboven voor "hoeveel gerelateerde records heeft dit ding" (bv. # API calls vanuit deze agent). Eén klik = de gefilterde lijst.

### Tekst & toon

- Engels. Korte zinnen. Geen Latijnse leenwoorden waar een Germaans alternatief bestaat ("set up", niet "configure"; "more info", niet "additional information").
- Geen marketing-taal in de UI. ("World-class observability" → "See every call this agent made.")
- Geen call-home, geen externe links in de listing-HTML (App Store regel; zie [CLAUDE.md](../CLAUDE.md#app-store-positioning-rules)).
- Help-tekst op velden is één zin. Twee zinnen alleen als de eerste een definitie geeft en de tweede de implicatie.

### Kleur

We laten Odoo's kleuren staan. We voegen geen eigen CSS toe. Op één plek mogen we het accent (`#9b99ff`) gebruiken: in de gif/banner in `static/description/`. Niet in de Odoo-UI zelf.

### Don'ts (op-volgorde-van-overtreding)

1. **Geen tweede top-level menu**. Alles onder "MCP Pro". Stuk dat niet past → submenu of helemaal weglaten.
2. **Geen modale "Are you sure?"** als undo bestaat (lifecycle-acties zijn omkeerbaar tot revoke — alleen revoke krijgt een bevestiging).
3. **Geen banners op elke view.** Eén discrete About/Promo-pagina onder Configuration is de plek voor pitch.
4. **Geen `attrs=` in views** (Odoo 19 deprecated). Gebruik `invisible=`, `readonly=`, `required=` direct.
5. **Geen externe links in `static/description/index.html`** behalve `mailto:` en canonieke YouTube — App Store-regel.

## Hoe verifieer je dit?

Zie [FEEDBACK.md](FEEDBACK.md). De korte versie:

- **Menu-structuur**: er is een Python test die telt hoeveel top-level menu's deze module aanmaakt — die moet `1` zijn.
- **Empty states**: smoke-tour klikt naar elke lijst en verwacht `.o_view_nocontent_smiling_face`.
- **Lifecycle states**: aparte tour die elke transitie via de header-knoppen doorloopt.
- **Visual**: `ui-feedback` skill draait Playwright tegen de lokale Odoo en kijkt of accent-paars niet in de UI lekt en of er maar één app-tegel op `/odoo` staat met de naam "MCP Pro".

Wijzigt iets aan deze regels? Eerst dit document aanpassen, dan de test, dan de code.
