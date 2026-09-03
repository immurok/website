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

Two small generators keep parts of the site from drifting. Run both before
deploying if you touched their inputs.

```bash
# Per-language FAQ pages (ja, es, pt, de, ko, ru, nl, pl, id, zh-hans, zh-hant).
# Translations live inside the script; edit there, then regenerate.
# --check also fails if Simplified and Traditional Chinese have swapped
# vocabulary (软件/軟體, 固件/韌體, ...), which is easy to do by hand.
python3 tools/build-lang-pages.py
python3 tools/build-lang-pages.py --check   # CI-friendly staleness check

# sitemap.xml, discovered from the files actually on disk.
# Run it after `hugo -d ../blog` and after build-lang-pages.py.
python3 tools/build-sitemap.py
python3 tools/build-sitemap.py --check
```

Analytics and the cookie-consent banner live in one place, `js/analytics.js`,
loaded by every page with `<script src="/js/analytics.js"></script>`. Do not
inline a second copy: `/download/` once shipped without one and disappeared
from GA4 entirely. To check that no page is missing it:

```bash
for f in $(find . -name "*.html" -not -path "./blog-src/*" -not -path "./.wrangler/*" -not -path "./3d/*"); do
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

```bash
# 1. Build the blog
cd website/blog-src
hugo -d ../blog

# 2. Regenerate the language pages and the sitemap
cd ..
python3 tools/build-lang-pages.py
python3 tools/build-sitemap.py

# 3. Deploy to Cloudflare Pages
npx wrangler pages deploy . --project-name=immurok
```

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
