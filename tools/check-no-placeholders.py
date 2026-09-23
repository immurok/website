#!/usr/bin/env python3
"""Refuse to let REPLACE_ME placeholders reach the public website mirror.

The shop config (Storefront token, shop domain, variant gids) lives in
index.html as data-* attributes and is filled in by hand after the Shopify
store exists. Until then the file carries REPLACE_ME_* markers. website/ is
rsynced to a public GitHub repo and deployed as-is, so a marker that slips
through is a visibly broken Buy button on the live site, and in the mirror it
is a permanent record that the store was never wired up.

This runs from scripts/sync-github.sh before the website rsync, and can be run
by hand at any time.

Usage:
    python3 tools/check-no-placeholders.py   # exit 1 and list file:line hits
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Built by concatenation so this file is not its own first finding.
MARKER = 'REPLACE' + '_ME'

# .wrangler/ is Cloudflare's local state, node_modules/ third-party code, and
# blog-src/themes/ a vendored Hugo theme. None of the three is ours to fix and
# none of the three is synced.
SKIP_DIRS = {'.wrangler', 'node_modules', '.git'}
SKIP_PATHS = {os.path.join('blog-src', 'themes')}
# This file names the marker in its own docstring, and holds no config of its own.
SKIP_FILES = {os.path.join('tools', 'check-no-placeholders.py')}


def hits(root):
    """Yield (relative path, line number) for every line carrying the marker."""
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS
                       and os.path.normpath(os.path.join(rel_dir, d)) not in SKIP_PATHS]
        for name in sorted(filenames):
            path = os.path.join(dirpath, name)
            if os.path.normpath(os.path.relpath(path, root)) in SKIP_FILES:
                continue
            try:
                with open(path, 'rb') as f:
                    raw = f.read()
            except OSError:
                continue
            if b'\0' in raw or MARKER.encode() not in raw:
                continue
            text = raw.decode('utf-8', errors='replace')
            for n, line in enumerate(text.split('\n'), 1):
                if MARKER in line:
                    yield os.path.relpath(path, root), n


def main():
    found = sorted(hits(ROOT))
    if found:
        print('%s placeholders are still present in website/:' % MARKER, file=sys.stderr)
        for path, line in found:
            print('  %s:%d' % (path, line), file=sys.stderr)
        return 1
    print('no placeholders')
    return 0


if __name__ == '__main__':
    sys.exit(main())
