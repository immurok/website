#!/usr/bin/env python3
"""Tell Bing (and everyone else on IndexNow) which URLs changed.

ChatGPT, Copilot and DuckDuckGo all search through Bing's index, and Bing
crawls a small site like this one slowly. IndexNow lets us push the URLs we
just deployed instead of waiting. One POST covers Bing, Yandex, Naver, Seznam
and the other participating engines.

The key is the file /049f2f4f21db482b8ed9d99e58abdd9f.txt at the site root, which the
engines fetch once to prove we own the host. Do not rotate it without also
updating KEY below.

Usage (after `wrangler pages deploy`):
    python3 tools/indexnow.py                 # every URL in both sitemaps
    python3 tools/indexnow.py /blog/new-post/ # just these paths
    python3 tools/indexnow.py --dry-run
"""

import argparse
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
HOST = "immurok.com"
KEY = "049f2f4f21db482b8ed9d99e58abdd9f"
ENDPOINT = "https://api.indexnow.org/indexnow"


def sitemap_urls():
    urls = []
    for name in ('sitemap.xml', os.path.join('blog', 'sitemap.xml')):
        path = os.path.join(ROOT, name)
        if os.path.exists(path):
            urls += re.findall(r'<loc>([^<]+)</loc>', open(path, encoding='utf-8').read())
    return sorted(set(urls))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('paths', nargs='*', help='site paths, e.g. /blog/foo/; default: every sitemap URL')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    urls = ['https://%s%s' % (HOST, p if p.startswith('/') else '/' + p) for p in args.paths] or sitemap_urls()
    if not urls:
        print('nothing to submit', file=sys.stderr)
        return 1
    body = {"host": HOST, "key": KEY, "keyLocation": "https://%s/%s.txt" % (HOST, KEY), "urlList": urls}
    if args.dry_run:
        print(json.dumps(body, indent=2))
        return 0
    req = urllib.request.Request(ENDPOINT, data=json.dumps(body).encode(),
                                 headers={'Content-Type': 'application/json; charset=utf-8'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print('IndexNow: HTTP %d for %d urls' % (r.status, len(urls)))
    except urllib.error.HTTPError as e:
        print('IndexNow: HTTP %d %s' % (e.code, e.read().decode(errors='replace')[:200]), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
