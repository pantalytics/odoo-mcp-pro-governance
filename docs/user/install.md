---
title: How to install and update MCP Pro Governance
knowledge_article_id: 103
last_synced: 2026-05-20
---

# How to install and update MCP Pro Governance

This guide walks you through three questions. By the end, you know exactly which route to use — and whether you should do it yourself or hand it to your implementation partner.

It takes about 2 minutes to read.

> **Note on naming:** *MCP Pro* is the AI connector that links Claude, ChatGPT, Cursor, or Gemini to your Odoo. *MCP Pro Governance* (this add-on) is the free in-app companion that gives you an audit log of every MCP call and lets you scope API keys to user roles. You can use MCP Pro without this add-on — but you lose the in-app visibility.

---

## Question 1 — Where does your Odoo run?

The URL alone won't tell you: Odoo Online and Odoo.sh production databases both use `.odoo.com` addresses. The reliable checks are:

| Check | What it tells you |
|---|---|
| **Your invoice from Odoo** | It will say *Odoo Online*, *Odoo.sh*, or you don't have an invoice from Odoo at all (then you're self-hosted). |
| **Do you have an Odoo.sh project?** | Log in at [www.odoo.sh](https://www.odoo.sh). If you see a project, that's your hosting. |
| **Ask whoever sends you the bill** | If someone else set this up, they know. |

### → If you have Odoo Online

You **cannot** install this add-on on Odoo Online — Odoo's platform blocks all third-party apps.

But you can still use the MCP Pro service itself (the AI connector). The MCP server runs outside Odoo and works with any Odoo hosting, Online included. Set it up at [pantalytics.com/apps/odoo-mcp-server](https://pantalytics.com/apps/odoo-mcp-server).

What you give up by not installing this add-on:

- No in-app audit log of MCP calls
- No scoped API keys bound to user roles

If you want those features, you'd need to migrate to Odoo.sh or a self-hosted setup first. Email [support@pantalytics.com](mailto:support@pantalytics.com) if you're considering it.

### → If you have Odoo.sh or Self-hosted

Continue to Question 2.

---

## Question 2 — Who manages your Odoo?

| Who clicks around in the technical side of Odoo? | Then |
|---|---|
| **My implementation partner or IT team** | Send them this page. You're done. |
| **I do it myself, and I'm comfortable with Git** | Continue to Question 3. |
| **I do it myself, but I'm not technical** | Use Route A below — it's the only non-technical route. |

**Link to send to your partner:**
[apps.odoo.com/apps/modules/19.0/pan_mcp_pro_governance](https://apps.odoo.com/apps/modules/19.0/pan_mcp_pro_governance)

---

## Question 3 — Are you installing for the first time, or updating?

The routes below cover both. Pick the one that matches your situation.

| Your situation | Use route |
|---|---|
| Odoo.sh, non-technical, want it working today | **Route A** (Deploy button) |
| Odoo.sh, technical / partner, want clean updates long-term | **Route B** (submodule + Dependabot) |
| Self-hosted | **Route C** (ZIP or git clone) |
| Implementation partner handles it | Send them this page |

> **One thing to know about all three routes:** this repository bundles its two OCA dependencies as sibling folders (`pan_mcp_auditlog` and `pan_mcp_user_role`) next to the main add-on. You install one package and get three addons in your Apps menu. No separate OCA download, no extra entries in `requirements.txt`. The two bundled folders are renamed copies of OCA `auditlog` and `base_user_role` (see [NOTICE.md](../../NOTICE.md)).

---

## Route A — Deploy on Odoo.sh (the one-click route)

**Use this if:** you have Odoo.sh, you want MCP Pro Governance working in five minutes, and you don't mind doing updates manually.

**How to install:**

1. Go to the [MCP Pro listing on the App Store](https://apps.odoo.com/apps/modules/19.0/pan_mcp_pro_governance).
2. Click **Deploy on Odoo.sh** and pick your project.
3. Odoo prepares a new build in your Odoo.sh project with the add-on ready to go. *(Exactly which branch the code lands on can vary — your Odoo.sh dashboard will show you a new build appear; that's the one to open.)*
4. Open the new build, go to **Apps**, search *MCP Pro*, and click **Install**. The two OCA addons install automatically as dependencies because they ship in the same package.
5. Test that your day-to-day work still functions.
6. In the Odoo.sh dashboard, promote the branch to **Staging**, then to **Production**, by dragging it between the columns.
7. In each environment, install MCP Pro from the Apps menu once. Merging branches in Odoo.sh moves the *code*, not the *installed-app state*, so you install it per environment.

**How to update:** click **Deploy on Odoo.sh** again. It prepares a new build with the latest version. Repeat steps 4–7.

**Honest trade-off:** every update creates a fresh build in your Odoo.sh project. After several updates you accumulate branches. If that bothers you, ask your partner about Route B.

---

## Route B — Git submodule with Dependabot (the recommended route for technical admins)

**This route is for your implementation partner or a technical admin.** Skip it if you're not comfortable with Git and pull requests.

**Use this if:** you have Odoo.sh, you already manage your repository with Git, and you want updates to feel as automatic as the Odoo ecosystem allows.

**How to install (one-time, ~10 minutes):**

1. In your Odoo.sh GitHub repository, add MCP Pro as a submodule. Note the submodule path: the repository contains three sibling add-on folders (`pan_mcp_auditlog`, `pan_mcp_user_role`, `pan_mcp_pro_governance`), so you point Odoo.sh's `addons_path` at the *repo root*, not at one folder inside it.

   ```bash
   git submodule add -b 19.0 https://github.com/pantalytics/odoo-mcp-pro-governance.git addons/pan_mcp_pro_governance_repo
   ```

2. In your Odoo.sh project settings, make sure `addons/pan_mcp_pro_governance_repo` is on the `addons_path`. Odoo will then discover all three sibling folders.
3. Commit and push.
4. Odoo.sh builds a development branch automatically. Open it, install MCP Pro from the Apps menu (the two OCA addons install as dependencies), test, then promote to staging and production.
5. Add `.github/dependabot.yml` to your repo:

   ```yaml
   version: 2
   updates:
     - package-ecosystem: "gitsubmodule"
       directory: "/"
       schedule:
         interval: "daily"
   ```

**How updates work from now on:**

1. When we release a new version, Dependabot opens a Pull Request in your repo (usually within 24 hours). You get an email.
2. Review the PR — the description shows what changed. Merge it to a development branch.
3. Odoo.sh builds and tests automatically. If it looks good, promote dev → staging → production.
4. In each environment, go to **Apps → MCP Pro → ⋮ → Upgrade**.

This is the closest thing to "auto-updates" that the Odoo ecosystem offers today. And because the OCA dependencies live in the same submodule, a single Dependabot PR brings everything along — no parallel submodules for `OCA/server-tools` or `OCA/server-backend` to keep in sync.

---

## Route C — Self-hosted (ZIP or git clone)

**This route is for your IT admin.** You need shell access to the server running Odoo.

**Use this if:** you don't use Odoo.sh. You run Odoo on your own server, in Docker, or on-premise.

**How to install:**

1. Clone the repo, or download the ZIP from the [App Store](https://apps.odoo.com/apps/modules/19.0/pan_mcp_pro_governance) and unzip it:

   ```bash
   git clone -b 19.0 https://github.com/pantalytics/odoo-mcp-pro-governance.git
   ```

2. Add the *repo root* to your `addons_path` (the directory list in `odoo.conf`). All three sibling folders — `pan_mcp_auditlog`, `pan_mcp_user_role`, and `pan_mcp_pro_governance` — become installable from that one entry.
3. Restart Odoo.
4. Log in, turn on developer mode, go to **Apps → Update Apps List**, search *MCP Pro*, click **Install**. The two OCA addons install automatically as dependencies.

**How to update:**

1. `git pull` in the repo (or download a fresh ZIP from the App Store and replace the folder).
2. Restart Odoo.
3. **Apps → MCP Pro → ⋮ → Upgrade**.

There is no notification when a new version is available on the App Store. To get an email per release, go to our [GitHub repo](https://github.com/pantalytics/odoo-mcp-pro-governance) and click **Watch → Custom → Releases**.

### Already running OCA `auditlog` or `base_user_role` from another source?

Our bundle ships its OCA dependencies under renamed slugs (`pan_mcp_auditlog`, `pan_mcp_user_role`) but keeps the upstream Python model names (`auditlog.rule`, `res.users.role`, …). If you already have the OCA originals installed in the same database, the install will fail with a model-registration conflict. Pick one of the two:

1. **Use the OCA originals.** Remove our bundled folders from the `addons_path` and edit `pan_mcp_pro_governance/__manifest__.py` to list the upstream slugs (`auditlog`, `base_user_role`) under `depends`. Reinstall.
2. **Use the Pantalytics bundle.** Uninstall the OCA originals from your database, then install MCP Pro from this repository.

For fresh Odoo installs — every "Deploy on Odoo.sh" flow from apps.odoo.com falls in this category — neither OCA original is present, so option 2 is the default and works without configuration. See [NOTICE.md](../../NOTICE.md) for the full rationale.

---

## What about "Import Module" in Odoo's Apps menu?

If you turn on developer mode and open the Apps menu, you'll see an **Import Module** option. You can drag a ZIP onto it and Odoo installs the module. **Don't use this for MCP Pro Governance in production.** Here's why.

- **It doesn't survive a rebuild.** The uploaded module lives in the database's filestore, not in your `addons_path` on disk. On Odoo.sh, every code push or restart rebuilds the container and your module disappears. On Docker, the same thing happens if the filestore volume isn't persistent.
- **You can't tell which version is installed.** There's no Git history, no `requirements.txt`, no link back to the App Store. Future you (or your partner) has no way to audit what's running.
- **There's no update path.** No notification when a new version ships. Updating means deleting the old upload, uploading a fresh ZIP, and hoping the schema migration is clean.
- **It's a developer convenience, not a deployment method.** The option exists so developers can try a module quickly on a local machine without touching `addons_path`. For anything you actually run a business on, use Route A, B, or C above.

If you've already used Import Module on a production database: don't panic, but before your next Odoo.sh build or container restart, install MCP Pro through one of the supported routes so you don't lose it.

---

## What if the upgrade fails?

Odoo's *Apps → Upgrade* can sometimes fail because of schema conflicts or missing dependencies, especially across major version jumps. If that happens:

1. **Don't panic and don't try to fix it by reinstalling.** The error message contains what we need.
2. Take a screenshot of the full error.
3. Email it to [support@pantalytics.com](mailto:support@pantalytics.com) with which route you used (A, B, or C) and which version you came from. We usually reply within one business day.

If you're on Odoo.sh and you followed Route A or B, you can always roll back by reverting the merge commit on the production branch — your production database is untouched until a code change is deployed.

---

## Still stuck?

Email [support@pantalytics.com](mailto:support@pantalytics.com) with a screenshot of where you got stuck and which route you tried.
