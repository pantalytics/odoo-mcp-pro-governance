# Icon and banner — design brief

Two assets ship with the App Store listing. The current set matches
the **light theme** of `pantalytics.com/apps/odoo-mcp-server`: a soft
white-to-lavender gradient with the original blue-ring brand mark.

Regenerate with `python3 .local/regen_assets.py` (script lives at the
repo root, gitignored).

## Brand palette (light theme — used by these assets)

Source: `pantalytics-website/src/styles/global.css` (`@media light` scope).

- Background: `#ffffff` (primary), `#f4f5f7` (secondary), faint lavender wash
- Accent: `#5b58d8` (purple) — hover `#4a47c4`
- Text: `#001d21` primary, muted slate for taglines
- Brand mark: `pantalytics-brand/public/images/logo/icon-blue.png` —
  dark blue outer ring `#1a4f8c`, light inner ring `#c0d6e4`, white centre.

The dark-theme palette (`#001d21` background + `#9b99ff` accent) still
exists in the brand kit but is **superseded** for App Store assets so
they match the public product page.

## `icon.png`

- **Size:** 256 × 256 px (square)
- **Format:** PNG, RGBA, opaque
- **Style:** soft radial gradient (faint lavender highlight top-left
  → `#f4f5f7` edges) with the blue-ring mark centred at ~76% size and
  a subtle 4 px / 22 % drop shadow for depth.
- **Readable at 32 px favicon size.** The gradient survives downscale
  because it's low-contrast; the ring carries the recognition.
- **Don'ts:** no screenshots, no inner text, no high-contrast shadows
  that turn into a hard halo at small sizes.

## `banner.png`

- **Size:** 1200 × 600 px
- **Format:** PNG
- **Composition:** brand mark left (380 px, soft drop shadow), text
  block right — "MCP Pro" in dark `#001d21`, "Claude · ChatGPT ·
  Gemini · Copilot" in accent `#5b58d8`, tagline ("in your Odoo —
  with a full audit trail") in muted slate. The accent line matches
  search intent (people looking for an MCP / AI connector); the
  muted line carries the standalone-utility differentiator.
- **Background:** vertical gradient white → faint lavender, blended
  with a top-right radial purple wash for depth.

## Where they're referenced

- `__manifest__.py` → `images` → `static/description/banner.png`
- Odoo auto-discovers `static/description/icon.png` for the app tile.

When replacement assets land, drop them in this directory and they
surface in Odoo and on `apps.odoo.com` automatically.
