# immurok Website

Product website and blog for [immurok](https://immurok.com).

- **Main site**: Static HTML/CSS/JS
- **Blog**: Hugo-powered, outputs to `blog/`

## Directory Structure

```
website/
├── index.html              # Main product page
├── css/style.css           # Main site styles
├── js/main.js              # Main site scripts
├── img/                    # Main site images
├── blog-src/               # Hugo source (blog authoring)
│   ├── hugo.toml           # Hugo configuration
│   ├── content/posts/      # Blog posts (Markdown)
│   └── themes/immurok/     # Custom Hugo theme
└── blog/                   # Hugo build output (do not edit directly)
```

## Prerequisites

- [Hugo](https://gohugo.io/) (extended edition)
- [Wrangler](https://developers.cloudflare.com/workers/wrangler/) (for Cloudflare Pages deployment)

```bash
brew install hugo
npm install -g wrangler
```

## Local Development

### Main site

```bash
cd website
python3 -m http.server 8080
# Open http://localhost:8080
```

### Blog

Build the blog and preview the entire site:

```bash
cd website/blog-src
hugo -d ../blog
cd ..
python3 -m http.server 8080
# Blog at http://localhost:8080/blog/
```

Or use Hugo's live-reload server for blog development:

```bash
cd website/blog-src
hugo server --port 1313
# Blog at http://localhost:1313/blog/
```

## Writing a Blog Post

### 1. Create a post directory

Each post is a directory under `blog-src/content/posts/`:

```bash
mkdir -p blog-src/content/posts/my-new-post
```

### 2. Write the post

Create `index.md` inside the directory:

```markdown
---
title: "My New Post"
date: 2026-03-06
description: "A short summary shown on the blog list page."
tags: ["engineering", "ble"]
slug: "my-new-post"
---

Post content in Markdown...

![diagram](diagram.png)
```

**Front matter fields:**

| Field         | Required | Description                                  |
|---------------|----------|----------------------------------------------|
| `title`       | Yes      | Post title                                   |
| `date`        | Yes      | Publish date (`YYYY-MM-DD`)                  |
| `description` | Yes      | Summary shown on the list page               |
| `tags`        | No       | List of tags, e.g. `["engineering", "security"]` |
| `slug`        | No       | URL slug (defaults to directory name)        |
| `draft`       | No       | Set `true` to hide from production builds    |

### 3. Add images (optional)

Place images in the same directory as `index.md`:

```
blog-src/content/posts/my-new-post/
├── index.md
├── diagram.png
└── photo.jpg
```

Reference them with relative paths in Markdown:

```markdown
![alt text](diagram.png)
```

### 4. Preview locally

```bash
cd blog-src
hugo server --port 1313
```

### 5. Build for production

```bash
cd blog-src
hugo -d ../blog
```

## Generated Files

Four small generators keep parts of the site from drifting. Run them in this
order before deploying if you touched their inputs; every one has a `--check`
mode that exits 1 when its output is stale.

```bash
# English landing pages: /ik-1/ (product), /mac-mini/, /linux/, /windows/,
# /ai-agents/, /vs/touch-id/, /vs/yubikey/, /about/, /contact/, /changelog/.
# Each page is a fragment in tools/pages/<name>.html (JSON meta comment +
# <main> contents); the script adds the shared head/nav/footer, derives the
# FAQPage JSON-LD from the visible <details> blocks, and on /ik-1/ builds the
# Product node with per-country shipping from js/shipping-data.js.
# The footer columns and font list every page uses live in this script.
python3 tools/build-pages.py
python3 tools/build-pages.py --check

# Per-language FAQ + product pages (ja, es, pt, de, ko, ru, nl, pl, id,
# zh-hans, zh-hant). Translations live inside the script; edit there, then
# regenerate. --check also fails if Simplified and Traditional Chinese have
# swapped vocabulary (软件/軟體, 固件/韌體, ...), which is easy to do by hand.
python3 tools/build-lang-pages.py
python3 tools/build-lang-pages.py --check

# sitemap.xml, discovered from the files actually on disk, with <lastmod>
# from git (blog posts reuse Hugo's git-derived lastmod).
# Run it after `hugo -d ../blog`, build-pages.py and build-lang-pages.py.
python3 tools/build-sitemap.py
python3 tools/build-sitemap.py --check

# /llms.txt and /llms-full.txt for AI crawlers: product facts, the fifteen
# FAQ answers (read from index.html) and the blog index. Edit FACTS / SPECS
# in the script when the homepage numbers change.
python3 tools/build-llms.py
python3 tools/build-llms.py --check
```

The blog is built with `hugo --cleanDestinationDir -d ../blog` so removed
pages (tag and category lists are disabled in hugo.toml) do not linger in
`blog/`. `enableGitInfo` gives each post a `dateModified` from its last commit,
used in the BlogPosting JSON-LD and the sitemap.

Analytics and the cookie-consent banner live in one place, `js/analytics.js`,
loaded by every page with `<script src="/js/analytics.js"></script>`. Do not
inline a second copy: `/download/` once shipped without one and disappeared
from GA4 entirely. To check that no page is missing it:

```bash
for f in $(find . -name "*.html" -not -path "./blog-src/*" -not -path "./.wrangler/*" -not -path "./3d/*" -not -path "./tools/*" -not -name "qc.html"); do
  [ "$(grep -c 'js/analytics.js' "$f")" = "0" ] && echo "missing analytics: $f"
done
```

The FAQ answers on the homepage exist twice: in the `#faq` accordion, whose
text sits in the initial HTML rather than behind JS, and as `FAQPage` JSON-LD
in `<head>`. They must stay in sync,
or Google flags a content mismatch. Edit the visible text, then:

```bash
python3 tools/check-faq-sync.py         # fails if the two have drifted
python3 tools/check-faq-sync.py --fix   # regenerate the JSON-LD from the page
```

## Deployment

The entire `website/` directory is deployed to Cloudflare Pages.

`qc.html` is the internal factory QC manual (a copy of `qc/qc-app-manual-zh.html`
with a noindex tag). It is deployed but deliberately unlisted: robots.txt
disallows it, `_headers` adds `X-Robots-Tag: noindex`, the sitemap generator
never sees it (it only lists directories with an `index.html`), it carries no
analytics, and `scripts/sync-github.sh` excludes it from the public repo.

```bash
# 1. Build the blog
cd website/blog-src
hugo --cleanDestinationDir -d ../blog

# 2. Regenerate the landing pages, language pages, sitemap and llms.txt
cd ..
python3 tools/build-pages.py
python3 tools/build-lang-pages.py
python3 tools/build-sitemap.py
python3 tools/build-llms.py

# 3. Deploy to Cloudflare Pages
npx wrangler pages deploy . --project-name=immurok

# 4. Tell Bing (ChatGPT / Copilot search through it) what changed.
#    Submits every sitemap URL; pass paths to submit only those.
python3 tools/indexnow.py
```

The IndexNow key file (`<key>.txt` at the site root) must stay deployed; the
key is also hard-coded in `tools/indexnow.py`. Bing Webmaster Tools shows
submissions under IndexNow once the site is verified there.

Images: the hero and gallery photos are WebP with `srcset` (the original
4.5 MB hero PNG is gone). Convert new photos with `cwebp -q 80 -resize <w> 0`
at 960/1440/2048 (hero) or 1280/2560 (gallery) widths.

### Shopify order webhook (GA4 purchase backfill)

### Download redirects (`/download/<target>`)

`functions/download/[target].js` resolves `/download/mac`, `/download/win-x64`
and `/download/win-arm64` to the newest asset of the matching GitHub release
(`immurok/app-macos`, `immurok/app-win`) and answers with a 302, so the
download page never needs editing when a version ships. Results are cached at
the edge for 10 minutes, with a 7-day last-known-good copy used as a fallback
when GitHub is unreachable; if even that is missing the user is sent to the
repo's releases page instead of an error.

`GITHUB_TOKEN` must be set as a Pages secret. Without it the lookup runs
unauthenticated and GitHub rate-limits it per source IP (60 req/hour). Workers
share Cloudflare's egress IPs with every other Worker on the platform, so that
quota is usually already spent by other tenants and the lookup fails with 403
no matter how little traffic we have. A fine-grained token with no
permissions at all is enough for public repos (5000 req/hour, per token):

```bash
# GitHub -> Settings -> Developer settings -> Fine-grained tokens -> Generate:
# Repository access "Public repositories (read-only)", no permissions, long expiry.
npx wrangler pages secret put GITHUB_TOKEN --project-name=immurok
# Takes effect immediately, no redeploy needed. Failures show up in
# `wrangler pages deployment tail` as "download/<target>: GitHub API 403 ... token=NO".
```

`functions/api/shopify-order.js` receives Shopify's `orders/create` webhook
and replays every order to GA4 through the Measurement Protocol. The
checkout tag alone only reports buyers who accepted cookies and run no
blocker (about 56% of orders in the Sept/Oct 2026 audit); the webhook makes
the purchase count and revenue complete. Orders the browser already reported
are deduplicated by GA4 (same client id + same transaction id); the rest go
out under a synthetic client id and are tagged `cid_source=synthetic`.

One-time setup:

```bash
# 1. Shopify Admin -> Settings -> Notifications -> Webhooks: copy the signing
#    key shown at the bottom of the section ("All your webhooks will be
#    signed with ...") and store it as a Pages secret. GA_MEASUREMENT_ID and
#    GA_API_SECRET are the same ones /api/t uses.
npx wrangler pages secret put SHOPIFY_WEBHOOK_SECRET --project-name=immurok
npx wrangler pages secret list --project-name=immurok

# 2. Deploy (step 3 above), then back in the Webhooks section: Create webhook,
#    Event "Order creation", Format JSON, URL https://immurok.com/api/shopify-order.

# 3. "Send test notification" on the new webhook: the sample order carries
#    test=true, the function skips it and answers 200. Then watch the next
#    real order arrive in GA4 Realtime as a purchase with backfill=webhook.
npx wrangler pages deployment tail --project-name=immurok
```

Custom event parameters worth registering as custom dimensions in GA4
(Admin -> Custom definitions, event scope): `backfill`, `cid_source`,
`order_country`. Until then they are only visible in Realtime / DebugView.

Idempotency uses the `LIKES` KV namespace under the `ga_txn:` prefix
(7-day TTL); without the binding the function still forwards, it just
cannot suppress a Shopify redelivery. Tests: `node --test tests/`.

## Markdown Features

The blog theme supports:

- Headings (`##`, `###`)
- Bold, italic, inline `code`
- Bullet and numbered lists
- Blockquotes
- Code blocks with syntax highlighting
- Images
- Tables
- Horizontal rules (`---`)
- Links
