# BullSignal — thebusinessledger

This is an **Astro** project (NOT Hugo). Deployed on Cloudflare Pages via GitHub Actions.

---

## 🔒 PROTECTED FILES — NEVER MODIFY

The following files define the site's design, layout, and structure. **No automated session, scheduled task, blog post, or data update may ever modify these files.** If you are tempted to touch them for any reason, STOP and ask the user instead.

```
src/layouts/BaseLayout.astro       ← site-wide nav, ticker, footer
src/pages/index.astro              ← homepage design
public/styles/global.css           ← all site CSS
src/pages/markets/                 ← all markets pages
src/pages/company/[symbol].astro   ← company detail pages
src/pages/news/                    ← news page
src/pages/comparison/              ← comparison page
src/pages/tools/                   ← tools pages
src/pages/about.astro              ← about page
astro.config.mjs                   ← build config
package.json                       ← dependencies
```

---

## ✅ WHAT BLOG/SCHEDULED TASKS MAY TOUCH

Automated morning/evening market summary tasks are only allowed to create or modify:

| Allowed path | Purpose |
|---|---|
| `src/pages/blog/*.md` | Blog post markdown files |
| `public/images/*.{png,jpg,svg,avif}` | Blog banner images |
| `public/data/*.json` | Market data JSON files (prices, indices, etc.) |
| `scripts/fetch_market_data.py` | Data fetch script only |

**Nothing else.** Do not restructure, rename, or delete any file outside these paths.

---

## Project Structure

```
src/
  layouts/BaseLayout.astro   ← PROTECTED
  pages/
    index.astro              ← PROTECTED (homepage)
    blog/                    ← blog posts go here (*.md files)
    markets/                 ← PROTECTED
    company/                 ← PROTECTED
    news/                    ← PROTECTED
public/
  styles/global.css          ← PROTECTED
  data/                      ← JSON market data (safe to update)
  images/                    ← banner images (safe to add)
scripts/
  fetch_market_data.py       ← data pipeline (safe to update)
```

---

## Blog Post Format

New blog posts go in `src/pages/blog/YYYY-MM-DD-slug.md` with this frontmatter:

```markdown
---
layout: ../../layouts/PostLayout.astro
title: "Post Title Here"
date: "YYYY-MM-DD"
author: "Apurva Gupta"
excerpt: "Short description"
image: /images/banner-filename.png
tags: ["Tag1", "Tag2"]
---
```

Banner images go in `public/images/` (NOT `static/images/` — this is Astro, not Hugo).

---

## Git Rules

- Commit blog posts and data files together: `git add src/pages/blog/ public/images/ public/data/`
- Never `git add .` or `git add src/layouts/` or `git add src/pages/index.astro`
- Always use targeted `git add <specific-file>` — never blanket adds
