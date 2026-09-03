#!/usr/bin/env python3
"""Check that the homepage FAQ JSON-LD matches the accordion answers word for word.

The answers exist twice on purpose: in the <details> accordion, whose text is
in the initial HTML and so is readable by crawlers, and as FAQPage structured
data, which is the channel search engines and AI assistants parse directly. If
the two drift apart Google flags a content mismatch and can drop the rich
result, so this runs as a cheap guard.

Usage:
    python3 tools/check-faq-sync.py        # exit 1 on any mismatch
    python3 tools/check-faq-sync.py --fix  # rewrite the JSON-LD from the page
"""

import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INDEX = os.path.join(os.path.dirname(HERE), 'index.html')

ENTITIES = {'&ldquo;': '"', '&rdquo;': '"', '&amp;': '&', '&nbsp;': ' ',
            '&middot;': '·', '&ndash;': '–', '&mdash;': '—'}


def norm(fragment):
    """Flatten an HTML fragment to the text a reader actually sees."""
    text = re.sub(r'<[^>]+>', ' ', fragment)
    for k, v in ENTITIES.items():
        text = text.replace(k, v)
    return re.sub(r'\s+', ' ', text).strip()


def visible(html):
    start = html.index('<section class="section section-alt" id="faq">')
    section = html[start:html.index('</section>', start)]
    pairs = re.findall(r'<summary>(.*?)</summary>\s*<p>(.*?)</p>', section, re.S)
    return [(norm(q), norm(a)) for q, a in pairs]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--fix', action='store_true')
    args = ap.parse_args()

    html = open(INDEX, encoding='utf-8').read()
    pairs = visible(html)
    m = re.search(r'(<script type="application/ld\+json">\n)(.*?)(\n  </script>)', html, re.S)
    doc = json.loads(m.group(2))
    faq = next(n for n in doc['@graph'] if n.get('@type') == 'FAQPage')

    if args.fix:
        faq['mainEntity'] = [
            {"@type": "Question", "name": q,
             "acceptedAnswer": {"@type": "Answer", "text": a}}
            for q, a in pairs]
        body = '\n'.join('  ' + line for line in
                         json.dumps(doc, ensure_ascii=False, indent=2).split('\n'))
        with open(INDEX, 'w', encoding='utf-8') as f:
            f.write(html[:m.start(2)] + body + html[m.end(2):])
        print('rewrote FAQ JSON-LD from %d visible answers' % len(pairs))
        return 0

    entries = faq['mainEntity']
    problems = []
    if len(entries) != len(pairs):
        problems.append('count: %d visible, %d in JSON-LD' % (len(pairs), len(entries)))
    for (q, a), entry in zip(pairs, entries):
        if entry['name'] != q:
            problems.append('question differs: %r' % q[:60])
        if entry['acceptedAnswer']['text'] != a:
            problems.append('answer differs under: %r' % q[:60])

    if problems:
        print('FAQ JSON-LD is out of sync with the visible answers:', file=sys.stderr)
        for p in problems:
            print('  ' + p, file=sys.stderr)
        print('run with --fix to regenerate it from the page', file=sys.stderr)
        return 1
    print('FAQ JSON-LD matches the %d visible answers' % len(pairs))
    return 0


if __name__ == '__main__':
    sys.exit(main())
