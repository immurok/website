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
