#!/usr/bin/env python3
"""Regenerate website/sitemap.xml from the files that are actually on disk.

The old sitemap listed six `#anchor` URLs as if they were separate pages, which
they are not, and listed none of the blog posts, which are. This walks the built
site instead, so the file cannot drift again.

Run it after `hugo -d ../blog` and after tools/build-lang-pages.py.

Usage:
    python3 tools/build-sitemap.py
    python3 tools/build-sitemap.py --check    # exit 1 if sitemap.xml is stale
"""

import argparse
import os
import sys

SITE = "https://immurok.com"
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Directories that hold pages but are not pages themselves, or that must never
# be indexed. 3d/ is an iframe widget; blog-src/ is Hugo input.
SKIP_DIRS = {'.wrangler', '.git', '3d', 'blog-src', 'tools', 'css', 'js', 'img',
             'fw', 'manual', 'doc', 'functions'}

# The translated FAQ pages form one hreflang cluster with the homepage.
# Directory name -> hreflang value; Chinese needs a script subtag that a
# lowercase URL segment cannot carry.
LANG_DIRS = {
    'ja': 'ja', 'es': 'es', 'pt': 'pt', 'de': 'de', 'ko': 'ko', 'ru': 'ru',
    'nl': 'nl', 'pl': 'pl', 'id': 'id',
    'zh-hans': 'zh-Hans', 'zh-hant': 'zh-Hant',
}

PRIORITY = {
    '/': ('1.0', 'weekly'),
    '/download/': ('0.8', 'weekly'),
    '/blog/': ('0.9', 'weekly'),
}


def discover():
    urls = []
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        if 'index.html' not in filenames:
            continue
        rel = os.path.relpath(dirpath, ROOT)
        path = '/' if rel == '.' else '/%s/' % rel.replace(os.sep, '/')
        # Hugo emits taxonomy stubs; they add nothing and dilute the sitemap.
        if '/tags/' in path or '/categories/' in path or path.endswith('/posts/'):
            continue
        urls.append(path)
    return sorted(set(urls), key=lambda p: (p.count('/'), p))


def build():
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"',
             '        xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    cluster = ['/'] + ['/%s/' % d for d in LANG_DIRS]
    for path in discover():
        prio, freq = PRIORITY.get(path, ('0.7', 'monthly'))
        lines.append('  <url>')
        lines.append('    <loc>%s%s</loc>' % (SITE, path))
        if path in cluster:
            # Every member of the cluster must list every member, including
            # itself, or Google ignores the annotations.
            lines.append('    <xhtml:link rel="alternate" hreflang="en" href="%s/"/>' % SITE)
            for d, code in LANG_DIRS.items():
                lines.append('    <xhtml:link rel="alternate" hreflang="%s" href="%s/%s/"/>' % (code, SITE, d))
            lines.append('    <xhtml:link rel="alternate" hreflang="x-default" href="%s/"/>' % SITE)
        lines.append('    <changefreq>%s</changefreq>' % freq)
        lines.append('    <priority>%s</priority>' % prio)
        lines.append('  </url>')
    lines.append('</urlset>')
    return '\n'.join(lines) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    out = os.path.join(ROOT, 'sitemap.xml')
    new = build()
    if args.check:
        current = open(out, encoding='utf-8').read() if os.path.exists(out) else None
        if current != new:
            print('sitemap.xml is stale', file=sys.stderr)
            return 1
        print('sitemap.xml up to date (%d urls)' % new.count('<loc>'))
        return 0
    with open(out, 'w', encoding='utf-8') as f:
        f.write(new)
    print('wrote sitemap.xml with %d urls' % new.count('<loc>'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
