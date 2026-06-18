# Stappenplan — v17 / v18 / v19 ondersteuning

> Status: in uitvoering (2026-06-18). Doel: de app installeerbaar maken op
> Odoo 18 (en optioneel 17) naast de huidige 19, met één gedeelde
> codebase. Aanleiding: een prospect draait Odoo 18 en vraagt de app.
>
> **Voortgang (trunk `19.0` + release-branch `18.0`):**
> - ✅ Fase 0–2 — `compat.py` in alle drie de addons; governance + beide
>   OCA-forks versie-tolerant. Gesplitste security-XML; v19-gated rolform.
> - ✅ Fase 3 — **draait op echte Odoo 18** (wegwerp `odoo:18`-container):
>   **fresh-DB install van de hele stack slaagt** ("Registry loaded",
>   post_init_hook draait). Gefixte v18-breuken: `NewId`-import,
>   `models.Constraint` ×2, `group_privilege_id`, de auditlog-capture-engine
>   (`ThrowAwayCache`, vetted OCA-18.0-implementatie), het user-list view-anker,
>   en self-inclusive `implied_groups`.
> - ✅ **Volledige testsuite groen op BEIDE versies**: v19 `0 failed of 21`,
>   **v18 `0 failed of 72`** (governance + auditlog + user_role).
> - ✅ Fase 4 — `feat/v18-compat` gemerged in `19.0`; gedeelde fixes terug op trunk.
> - ✅ Fase 5 — `18.0`-release-branch (delta vs trunk = 3 manifest-versies +
>   governance data-lijst + user-list view-anker; al het Python is gedeeld).
> - 📌 Extra v18-werk dat nodig bleek (gedeeld, versie-tolerant):
>   - auditlog revert via `delattr` op <=18 (v18-framework flagt achtergebleven
>     class-patches); `tests/common.py` beheert de patch-lifecycle per test.
>   - test-compat (`USER_GROUPS_FIELD` op menu/user), privilege-tests geskipt <19.
>   - `implied_groups` = platte field-read (matcht v19; lege rol → lege set).
>   - key-owner rol impliceert `base.group_user` (nul-groepen-user triggert een
>     Odoo-18-core `max()`-bug in `_check_expiration_date`).
> - 🔎 **Eén v18-follow-up**: de wizard `x_available_role_ids` lost leeg op onder
>   de v18-compute (filter-logica is wél correct, handmatig geverifieerd) — test
>   geskipt op <19, vraagt nog uitzoekwerk.
> - ⏳ Scope 17: nog niet meegenomen (compat dekt `< 19` al; alleen een
>   17.0-release-branch + smoke-test resteert).

## Fase 3 — bevindingen op echte Odoo 18 (2026-06-18)

De v18-testopstelling (herbruikbaar):

```bash
docker pull odoo:18
docker run --rm --network local_default \
  -v "$PWD/pan_mcp_pro_governance:/mnt/extra-addons/pan_mcp_pro_governance" \
  -v "$PWD/pan_mcp_auditlog:/mnt/extra-addons/pan_mcp_auditlog" \
  -v "$PWD/pan_mcp_user_role:/mnt/extra-addons/pan_mcp_user_role" \
  odoo:18 odoo -d v18test --db_host db --db_user odoo --db_password odoo \
  --addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons \
  -i pan_mcp_pro_governance --test-enable \
  --test-tags=/pan_mcp_pro_governance,/pan_mcp_auditlog,/pan_mcp_user_role \
  --stop-after-init --without-demo=all
```

Onze addon hangt alleen aan `base` + `mail`, dus de **community** `odoo:18`
volstaat — geen enterprise-image nodig. Bij het draaien moeten de drie
manifest-versies tijdelijk op `18.0`-prefix (anders weigert Odoo te laden);
op de echte 18.0-branch is dat permanent.

**Status:** opgelost via **optie A** (zie hieronder) — bleek compacter dan
gevreesd: de v19-afhankelijkheid zat volledig in één klasse (`ThrowAwayCache`),
niet de hele engine. Restwerk voor een *groene testsuite* is nu alleen nog het
version-guarden van v19-fixtures in testcode.

### Bewijs: auditlog's capture-context is puur v19

`pan_mcp_auditlog`'s `_CleanCacheContext` bewaart/herstelt transaction-attributen
die in v18 niet bestaan (geverifieerd tegen lokale 18.0- én 19.0-broncode):

| Attribuut | v19 (`odoo/orm/environments.py`) | v18 (`odoo/api.py`) |
|---|---|---|
| `Transaction.field_data` / `field_data_patches` / `field_dirty` | ✅ slots op Transaction | ❌ — cache zit in los `Cache`-object (`_data/_dirty/_patches`) |
| `Environment._field_cache_memo` | ✅ | ❌ bestaat niet in v18 |

Het is dus geen veldnaam-rename maar een andere cache-architectuur. Conclusie:
**niet met de hand namaken** (giswerk op een audit-feature) — OCA's 18.0-auditlog
heeft hier z'n eigen implementatie.

### Beslispunt auditlog → gekozen: A

- **A. (gekozen)** Alleen de ene v19-specifieke klasse (`ThrowAwayCache`)
  version-gaten: v19-pad behouden, OCA's vetted 18.0-implementatie ernaast
  (`env.cache` swap). ~40 regels, geen dubbele engine. Auditlog blijft één
  codebase. Bleek de juiste keuze toen het divergente oppervlak één klasse
  bleek, niet de hele engine.
- **B. (verworpen)** Auditlog per-versie vendoren. Onnodig zwaar gegeven dat
  A zo klein uitviel.

## 1. Beslissing in één alinea

Eén gedeelde, **versie-tolerante** codebase op `main`. De code detecteert
de draaiende Odoo-versie at runtime (`odoo.release.version_info`) en kiest
de juiste veldnamen / datafiles. Per Odoo-serie leveren we uit via een
dunne release-branch (`17.0` / `18.0` / `19.0`) die een bijna byte-identieke
kopie van `main` is — het enige verschil is de `version`-prefix in de drie
manifests, omdat de App Store daarop sorteert.

Géén aparte, uit-elkaar-lopende branch per versie: dat geeft verschillende
git-histories en cherry-pick-pijn (de bekende OCA-onderhoudslast). De
compat-laag houdt de échte code overal gelijk, zodat een release-branch
puur een kopie is.

## 2. Waarom dit kan (en waar de breuk zit)

Odoo's eigen RFC (#15992) bevestigt: Python kan de versie detecteren en
kiezen wat-ie doet; alleen **datafiles** (XML) zijn niet runtime-schakelbaar.
De v18→v19-breuk in het groepenmodel is exact in kaart:

| Begrip | Odoo 19 | Odoo 18 / 17 | Op te vangen via |
|---|---|---|---|
| Groepen van een user | `group_ids` | `groups_id` | compat-helper (Python) |
| Doorgeërfde groepen | `all_implied_ids` | `trans_implied_ids` | compat-helper (Python) |
| Effectieve groepen | `all_group_ids` + `_compute_all_group_ids` | bestaat niet | override alleen op 19 registreren |
| Groep-categorie | `res.groups.privilege` + `privilege_id` | `category_id` → `ir.module.category` | versie-specifieke **XML** |
| Access-rights widget | `res_user_group_ids` + `_get_view_group_hierarchy()` | bestaat niet | versie-specifieke **XML** (18 valt terug op OCA-default) |
| `_get_group_ids()` | aanwezig | aanwezig | **gedeeld anker** — narrowing-kern blijft één implementatie |

OCA-deps zijn off-the-shelf beschikbaar per versie en dienen als referentie:
- `auditlog` → OCA/server-tools @ 17.0 / 18.0 / 19.0
- `base_user_role` → OCA/server-backend @ 17.0 / 18.0 / 19.0

Het 18↔19-verschil in die modules is bíjna volledig dezelfde groep-rename
die we toch al opvangen.

## 3. Architectuur

Drie forks, alle drie hetzelfde patroon (we forken de twee OCA-modules toch
al voor de App Store-rename + orphan-patch-fix):

```
pan_mcp_pro_governance/   ← ons addon
pan_mcp_auditlog/         ← OCA-fork (server-tools/auditlog)
pan_mcp_user_role/        ← OCA-fork (server-backend/base_user_role)
```

Per fork:

1. **`compat.py`** — detecteert de versie, levert de juiste namen:
   ```python
   from odoo.release import version_info
   ODOO = version_info[0]
   GROUPS_FIELD  = "group_ids"       if ODOO >= 19 else "groups_id"
   IMPLIED_FIELD = "all_implied_ids" if ODOO >= 19 else "trans_implied_ids"
   ```
2. **`__manifest__.py`** — **let op:** Odoo parst het manifest met
   `ast.literal_eval` (geverifieerd in v18 én v19). Dus géén imports,
   expressies of `if` in het manifest — alleen literals. De `data`-lijst kan
   dáárom niet runtime schakelen. De paar versie-specifieke datafiles zijn
   daarmee **de enige legitieme per-release-branch-delta** (naast de
   `version`-prefix). De `19.0`-trunk somt de 19+-bestanden op; de
   `18.0`-branch ruilt:
   - `security/groups_privilege_v19.xml` → `security/groups_legacy.xml`
   - laat `views/mcp_governance_role_views.xml` weg (widget is 19-only)
3. **Versie-specifieke XML** alleen waar het declaratief móet
   (privilege-records, rolform-widget). Rest blijft gedeeld.

> Correctie t.o.v. het oorspronkelijke idee: een manifest dat zichzelf op
> `version_info` aanpast is niet mogelijk (`literal_eval`). De Python-laag is
> wél runtime-tolerant; alleen de declaratieve datafiles vereisen een
> minimale, mergeable manifest-diff per branch.

## 4. Werk per fork

### 4a. `pan_mcp_pro_governance` (ons addon — kleinste schaal, eerst)

- [ ] `compat.py` toevoegen met `GROUPS_FIELD` / `IMPLIED_FIELD` / `ODOO`.
- [ ] In `models/` letterlijke veldnamen vervangen door compat-toegang:
      `res_users.py`, `ir_model_access.py`, `ir_rule.py`,
      `res_users_apikeys.py`, `res_users_apikeys_description.py`,
      `res_users_role.py`.
- [ ] `_compute_all_group_ids` / `all_group_ids`-override alleen actief op
      ≥19 (veld bestaat niet op 18). Narrowing op 18 leunt op
      `_get_group_ids` + de `ir.model.access` / `ir.rule`-overrides —
      **verifiëren** dat het access-pad op 18 echt door `_get_group_ids` loopt.
- [ ] `security/mcp_pro_governance_groups.xml` splitsen:
      `groups_v19.xml` (privilege-record + `privilege_id`) vs
      `groups_legacy.xml` (`category_id` direct op de groep).
- [ ] `views/mcp_governance_role_views.xml`: de `res_user_group_ids`-widget
      naar `role_form_v19.xml`; op 18 de OCA-default (platte `many2many_tags`).
- [ ] `hooks.py` nalopen op groep-veldnamen.
- [ ] `__manifest__.py`: dynamische `data`-lijst.

### 4b. `pan_mcp_auditlog` (OCA-fork)

- [ ] OCA 18.0 vs 19.0 van `auditlog` diffen.
- [ ] Verschillen achter compat vouwen (verwachting: klein).
- [ ] Manifest `data`-lijst dynamisch waar nodig.
- [ ] Orphan-patch-fix behouden (zie project-geheugen / v1.19.0).

### 4c. `pan_mcp_user_role` (OCA-fork)

- [ ] OCA 18.0 vs 19.0 van `base_user_role` diffen (vooral groep-rename).
- [ ] `role.py`, `user.py`, `wizards/create_from_user.py` via compat.
- [ ] Manifest `data`-lijst dynamisch waar nodig.

## 5. Fasering

1. **Fase 0 — werkbranch.** `feat/v18-compat` vanaf `19.0`/`main`.
2. **Fase 1 — bewijs op klein.** Alleen `pan_mcp_pro_governance` (4a)
   versie-tolerant maken. Lokaal testen op 18 én 19. Patroon bevestigd.
3. **Fase 2 — OCA-forks.** `pan_mcp_auditlog` (4b) en
   `pan_mcp_user_role` (4c).
4. **Fase 3 — groene CI op beide versies.** `make test` op een 18- en een
   19-container (fresh-DB install is de App Store-takedown-trigger).
5. **Fase 4 — merge naar `main`.** `main` is nu versie-agnostisch.
6. **Fase 5 — release-branches.** `18.0` (en evt. `17.0`) aanmaken als
   kopie; de drie manifest-`version`-prefixes pinnen; tag; upload.

## 6. Release-flow (saai = goed)

1. Werken doe je altijd op `main`.
2. Release: `git checkout 18.0` → `git merge main` → drie manifest-versies
   op `18.0.…` → tag → upload naar de App Store onder Odoo 18.
3. Bugfix: één commit op `main`, daarna mergen naar elke release-branch.
   Geen cherry-pick — de code ís gelijk.

> Niet doen: de manifest-`version` dynamisch uitrekenen voor de App Store.
> De importer wil historisch een statische, serie-geprefixte string; daar
> wil je een submissie niet op gokken. De drie regels handmatig pinnen op
> de release-branch is voorspelbaar.

## 7. Testen / feedback-loops

- Lokaal: een tweede docker-compose-profiel met het 18.0-image naast 19.0,
  zodat `make test` op beide draait (zie `docs/dev/FEEDBACK.md`).
- Harde eis: **fresh-DB install slaagt op 17/18/19** — dat is de #1
  App Store-takedown-trigger.
- `/ui-feedback` op 18 draaien: de platte menu-layout van 19 bestaat daar
  niet; checken dat de views niet lelijk degraderen.

## 8. Open beslissing

**Doen we 17 meteen mee, of eerst alleen 18 + 19?**

De compat-laag wordt dan een bereik (`>= 19`, `== 18`, `== 17`) i.p.v. een
18/19-knip — weinig extra werk, maar bepaalt nu de teststof en het aantal
release-branches. Voor de huidige prospect (Odoo 18) volstaat 18 + 19;
17 is laagdrempelig later toe te voegen omdat de OCA-deps er al zijn.

## Bronnen

- Odoo RFC #15992 — addons compatible with multiple versions
- OCA `oca-port` — per-version branches & forward/backport-pijn
- "What's New in Odoo 19" — `groups_id`→`group_ids`, privilege-model
- OCA/server-tools @ 18.0 `auditlog`; OCA/server-backend @ 18.0 `base_user_role`
