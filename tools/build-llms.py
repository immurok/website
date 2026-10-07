#!/usr/bin/env python3
"""Generate /llms.txt and /llms-full.txt for AI crawlers and assistants.

llms.txt (https://llmstxt.org) is a plain-Markdown summary of the site that
LLM-based crawlers can read in one request instead of rendering pages. The
short file is a map: what the product is, the facts assistants are asked for
most (price, platforms, shipping, security), and links to the pages that hold
the rest. The full file inlines the fifteen FAQ answers word for word and the
blog descriptions, so an answer engine can quote us instead of a reseller.

Everything comes from files that already exist so the two cannot drift:
  - FAQ answers: the visible #faq accordion in index.html (same source that
    check-faq-sync.py uses for the JSON-LD)
  - blog posts: front matter under blog-src/content/posts
  - specs, price, shipping window: SPECS / FACTS below (edit here when the
    homepage changes; check-no-placeholders.py does not cover these)

Usage:
    python3 tools/build-llms.py           # writes llms.txt and llms-full.txt
    python3 tools/build-llms.py --check   # exit 1 if either file is stale
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SITE = "https://immurok.com"

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location('check_faq_sync', os.path.join(HERE, 'check-faq-sync.py'))
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
visible = _mod.visible  # same FAQ parser the JSON-LD check uses

def country_count():
    src = open(os.path.join(ROOT, 'js', 'shipping-data.js'), encoding='utf-8').read()
    return len(json.loads(src[src.index('{'):src.rstrip().rstrip(';').rindex('}') + 1])['countries'])


FACTS = [
    ("Product", "immurok IK-1, a standalone wireless fingerprint key (Bluetooth LE) for desktop authentication"),
    ("What it does", "Screen unlock, sudo and admin prompts, SSH and Git commit signing, 1Password / Bitwarden / LastPass / Proton Pass unlock, TOTP codes, and a fingerprint gate for AI coding agents (Claude Code, Cursor, Codex, Copilot)"),
    ("Platforms", "macOS 13.0 or later (Apple Silicon and Intel), Windows 10 and 11 (x64 and Arm64), Linux (Ubuntu, Fedora, Arch, Debian and most other distributions). Not ChromeOS. Not a FIDO / passkey device"),
    ("Price", "US$69 one-time. No subscription, no account, no cloud. Apps and firmware updates are free"),
    ("Availability", "Pre-order at https://immurok.com/ik-1/ ; ships December 2026. Cancel for a full refund any time before it ships"),
    ("Shipping", "Ships from China, tracked, to %d countries. " % country_count() + "Rates shown per country before checkout. Import duties are the recipient's responsibility (DDU) except where marked as included"),
    ("Warranty and returns", "One-year limited warranty. Returns accepted for damaged or faulty devices within 7 days of delivery"),
    ("Security", "Fingerprint templates stored and matched on the device only. ECDH P-256 pairing, HMAC-signed events, ECDSA-signed firmware with anti-rollback, tamper switch wipes the key if the case is opened"),
    ("Licences", "macOS, Windows and Linux apps: Apache 2.0. Firmware and hardware: BSL 1.1, converting to Apache 2.0 in 2030. Source at https://github.com/immurok"),
    ("Company", "immurok is a trading name of Nervina Next Pte. Ltd., Singapore (UEN 202128549C), 24 Sin Ming Lane, #06-97, Midview City, Singapore 573970. Email hello@immurok.com"),
    ("Funding", "Kickstarter campaign closed 22 September 2026 with 4,634 backers and S$480,299 pledged"),
]

SPECS = [
    ("Connectivity", "Bluetooth LE; pairs with up to 2 computers (dual-host), one connected at a time"),
    ("Sensor", "Capacitive fingerprint sensor, under 500 ms match, up to 5 enrolled fingerprints"),
    ("Battery", "110 mAh LiPo, USB-C charging (charge only, no data), 1+ month per charge"),
    ("Body", "CNC anodized aluminium"),
    ("Size and weight", "44 x 44 x 14.2 mm, about 40 g"),
    ("GTIN", "00884400414250"),
]

PAGES = [
    ("/", "Homepage: features, compatibility, comparison with Touch ID and USB dongles, pricing, FAQ"),
    ("/ik-1/", "Product page: immurok IK-1 specifications, price, shipping, pre-order"),
    ("/mac-mini/", "Touch ID alternative for Mac mini, Mac Studio, iMac and clamshell MacBooks"),
    ("/linux/", "Fingerprint login, sudo and PAM on Linux"),
    ("/windows/", "Fingerprint sign-in on Windows desktops without Windows Hello hardware"),
    ("/ai-agents/", "A fingerprint gate for AI coding agents (imk run --agent)"),
    ("/vs/touch-id/", "immurok compared with Touch ID and the Magic Keyboard with Touch ID"),
    ("/vs/yubikey/", "immurok compared with YubiKey and FIDO security keys"),
    ("/download/", "Desktop apps for macOS, Windows and Linux, plus the user manual"),
    ("/about/", "Who makes immurok"),
    ("/contact/", "How to reach us"),
    ("/blog/", "Engineering notes and security deep-dives"),
]

LANGS = [
    ("ja", "日本語"), ("es", "Español"), ("pt", "Português"), ("de", "Deutsch"),
    ("ko", "한국어"), ("ru", "Русский"), ("nl", "Nederlands"), ("pl", "Polski"),
    ("id", "Bahasa Indonesia"), ("zh-hans", "简体中文"), ("zh-hant", "繁體中文"),
]

POLICIES = [
    ("Shipping policy", "https://checkout.immurok.com/policies/shipping-policy"),
    ("Refund policy", "https://checkout.immurok.com/policies/refund-policy"),
    ("Privacy policy", "https://checkout.immurok.com/policies/privacy-policy"),
    ("Terms of service", "https://checkout.immurok.com/policies/terms-of-service"),
]


def posts():
    out = []
    base = os.path.join(ROOT, 'blog-src', 'content', 'posts')
    for name in sorted(os.listdir(base)):
        md = os.path.join(base, name, 'index.md')
        if not os.path.exists(md):
            continue
        text = open(md, encoding='utf-8').read()
        fm = text.split('---', 2)[1]
        get = lambda k: (re.search(r'^%s:\s*"?(.*?)"?\s*$' % k, fm, re.M) or [None, ''])[1]
        if get('draft') == 'true':
            continue
        slug = get('slug') or name
        out.append((get('date')[:10], get('title'), get('description'), '%s/blog/%s/' % (SITE, slug)))
    return sorted(out, reverse=True)


def faq():
    html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    return visible(html)


def short():
    L = ['# immurok', '',
         '> immurok IK-1 is a standalone wireless fingerprint key for Mac, Windows and Linux. '
         'One touch unlocks the screen, approves sudo and admin prompts, signs SSH and Git commits, '
         'unlocks password managers and gates AI coding agents. US$69, no subscription, no cloud. '
         'Pre-order, ships December 2026.', '']
    L.append('## Key facts')
    L.append('')
    for k, v in FACTS:
        L.append('- %s: %s' % (k, v))
    L.append('')
    L.append('## Specifications')
    L.append('')
    for k, v in SPECS:
        L.append('- %s: %s' % (k, v))
    L.append('')
    L.append('## Pages')
    L.append('')
    for path, desc in PAGES:
        L.append('- [%s](%s%s): %s' % (path, SITE, path, desc))
    L.append('')
    L.append('## FAQ pages in other languages')
    L.append('')
    L.append('Same fifteen answers as the English FAQ, translated: ' +
             ', '.join('[%s](%s/%s/)' % (name, SITE, code) for code, name in LANGS) + '.')
    L.append('')
    L.append('## Policies')
    L.append('')
    for name, url in POLICIES:
        L.append('- [%s](%s)' % (name, url))
    L.append('')
    L.append('## Blog')
    L.append('')
    for date, title, desc, url in posts():
        L.append('- [%s](%s) (%s)' % (title, url, date))
    L.append('')
    L.append('## Optional')
    L.append('')
    L.append('- [Full version with every FAQ answer](%s/llms-full.txt)' % SITE)
    L.append('- [Source code](https://github.com/immurok)')
    L.append('- [User manual (PDF)](%s/manual/IK-1_User_Manual_EN.pdf)' % SITE)
    L.append('- [Discord](https://discord.gg/beavzPCanZ)')
    return '\n'.join(L) + '\n'


def full():
    L = short().rstrip('\n').split('\n')
    # Drop the "Optional" pointer to ourselves.
    cut = L.index('## Optional')
    L = L[:cut]
    L.append('## Frequently asked questions')
    L.append('')
    for q, a in faq():
        L.append('### %s' % q)
        L.append('')
        L.append(a)
        L.append('')
    L.append('## Blog post summaries')
    L.append('')
    for date, title, desc, url in posts():
        L.append('### %s' % title)
        L.append('')
        L.append('%s. %s' % (date, desc))
        L.append('')
        L.append(url)
        L.append('')
    L.append('## Links')
    L.append('')
    L.append('- Source code: https://github.com/immurok')
    L.append('- User manual (PDF): %s/manual/IK-1_User_Manual_EN.pdf' % SITE)
    L.append('- Discord: https://discord.gg/beavzPCanZ')
    L.append('- X: https://x.com/immurok_dev')
    return '\n'.join(L) + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    outputs = {'llms.txt': short(), 'llms-full.txt': full()}
    stale = []
    for name, body in outputs.items():
        path = os.path.join(ROOT, name)
        current = open(path, encoding='utf-8').read() if os.path.exists(path) else None
        if args.check:
            if current != body:
                stale.append(name)
        elif current != body:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(body)
            print('wrote %s (%d bytes)' % (name, len(body.encode('utf-8'))))
    if args.check:
        if stale:
            print('stale: %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('llms.txt and llms-full.txt up to date')
    return 0


if __name__ == '__main__':
    sys.exit(main())
