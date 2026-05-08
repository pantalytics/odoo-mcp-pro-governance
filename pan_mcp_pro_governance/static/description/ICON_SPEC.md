# Icon and banner — design brief

Two assets ship with the App Store listing. A baseline pair generated
from the Pantalytics brand kit (hollow blue ring on a dark tile) lives
in this directory now; this brief is for the *replacement* set that a
designer should produce before v1.0.

## Brand palette (current)

Source: `pantalytics-brand/public/downloads/pantalytics-colors.css`.

- Background dark: `#001d21` (primary), `#002328` (secondary)
- Accent: `#9b99ff` (purple) — hover `#7370ff`
- Text on dark: `#ffffff`, secondary `rgba(255,255,255,0.6)`

Older material used navy `#1b3a5c` + gold `#e8a317`; that palette is
**superseded** for new assets. Existing logo PNGs in the brand kit
(`icon-blue.png`, `icon-gold.png`) still ship the legacy ring colors
— use them as the brand mark on the new dark background.

## `icon.png`

- **Size:** 256 × 256 px (square)
- **Format:** PNG, RGBA. May be opaque (dark tile) or transparent.
- **Style:** simple glyph, single subject, readable at 32 px favicon size
- **Current baseline:** hollow blue brand ring with white centre on a
  `#001d21` tile. Reads as a generic Pantalytics tile — fine for v0.x,
  but every Pantalytics app would look identical. The replacement
  should add a glyph that distinguishes *this* app from `pan_outlook_pro`
  and any future Pantalytics modules.
- **Motif idea:** a shield, badge or lock superimposed on a network /
  agent node to signal governance of distributed AI actors. Keep it
  abstract — "key with padlock" reads too much like an auth app.
- **Don'ts:** no screenshots, no inner text, no gradients, no drop
  shadows. Must survive flat rendering on the App Store tile.

## `banner.png`

- **Size:** 1200 × 600 px
- **Format:** PNG
- **Content:** wide brand hero above the fold of the App Store
  description page. The current baseline is the brand mark + product
  wordmark on the dark background. A replacement could show a
  dashboard-style composition (agent list left, audit log right) or
  an abstract pattern with the wordmark.
- **Palette:** dominant `#001d21`, accent `#9b99ff` in small doses,
  text white or `rgba(255,255,255,0.6)`.

## Where they're referenced

- `__manifest__.py` → `images` → `static/description/banner.png`
- Odoo auto-discovers `static/description/icon.png` for the app tile.

When replacement assets land, drop them in this directory and they
surface in Odoo and on `apps.odoo.com` automatically.
