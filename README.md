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

## Deployment

The entire `website/` directory is deployed to Cloudflare Pages.

```bash
# 1. Build the blog
cd website/blog-src
hugo -d ../blog

# 2. Deploy to Cloudflare Pages
cd ..
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
