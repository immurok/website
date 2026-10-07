#!/usr/bin/env python3
"""Generate the English landing pages under website/<path>/index.html.

Each page is a fragment in tools/pages/<name>.html: a JSON block inside a
leading <!--meta ... --> comment, then the <main> contents. This script wraps
the fragment in the shared chrome (head, nav, footer, scripts) so the pages
cannot drift from each other or from the homepage, and derives the structured
data from the fragment itself:

  - WebPage + BreadcrumbList for every page
  - FAQPage from any <details class="faq-item"> blocks in the fragment, so the
    JSON-LD is the visible text by construction
  - Product with per-country shipping and the return policy on the product
    page (meta "product": true), built from js/shipping-data.js
  - the full Organization entity on every page

Meta keys:
  path         "/mac-mini/"  (required)
  title        <title> and og:title (required)
  description  meta description (required)
  type         schema.org WebPage subtype, default "WebPage"
  crumbs       [["Blog", "/blog/"], ...] parents between Home and this page
  og_image     absolute URL, default the site share image
  shop         true to load the buy flow (shop.js + shipping data + drawer)
  product      true to emit the Product node with shipping details
  noindex      true for a link-only page: robots noindex meta (also add the
               directory to build-sitemap.py SKIP_DIRS, robots.txt, _headers)
  scripts      extra <script src> paths appended after main.js

Usage:
    python3 tools/build-pages.py           # writes every page
    python3 tools/build-pages.py --check   # exit 1 if any page is stale
"""

import argparse
import datetime
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PAGES_DIR = os.path.join(HERE, 'pages')
SITE = "https://immurok.com"
OG_IMAGE = SITE + "/img/og-image.jpg"

FONTS = ("https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700"
         "&family=Space+Grotesk:wght@300;400;500;600;700"
         "&family=JetBrains+Mono:wght@400;500&display=swap")

# Same entity on every page. Keep in step with the Organization node in
# index.html (check-faq-sync.py rewrites that file's JSON-LD, so edit both).
ORG = {
    "@type": "Organization",
    "@id": SITE + "/#org",
    "name": "immurok",
    "url": SITE + "/",
    "logo": {"@type": "ImageObject", "url": SITE + "/favicon-512.png", "width": 512, "height": 512},
    "email": "hello@immurok.com",
    "sameAs": [
        "https://github.com/immurok",
        "https://x.com/immurok_dev",
        "https://discord.gg/beavzPCanZ",
        "https://www.kickstarter.com/projects/immurok/immurokwireless-fingerprint-auth-key-for-mac-and-linux",
    ],
    "contactPoint": {
        "@type": "ContactPoint",
        "contactType": "customer support",
        "email": "hello@immurok.com",
        "url": SITE + "/contact/",
        "availableLanguage": ["en"],
    },
    "parentOrganization": {
        "@type": "Organization",
        "name": "Nervina Next Pte. Ltd.",
        "foundingDate": "2021",
        "identifier": {"@type": "PropertyValue", "propertyID": "UEN", "value": "202128549C"},
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "24 Sin Ming Lane, #06-97, Midview City",
            "addressLocality": "Singapore",
            "postalCode": "573970",
            "addressCountry": "SG",
        },
    },
}

PRODUCT_IMAGES = [
    "/img/device-in-hand-1920.webp",
    "/img/leather-case-1920.webp",
]

NAV = '''  <nav class="nav" id="nav">
    <div class="nav-inner">
      <a href="/" class="nav-logo">
        <img class="nav-logo-wordmark" src="/img/figma/logo-wordmark.png" width="187" height="34" alt="immurok">
        <img class="nav-logo-mark" src="/img/figma/logo-mark.png" width="33" height="28" alt="immurok">
      </a>
      <div class="nav-links">
        <a href="/#features">Features</a>
        <a href="/ik-1/">Shop</a>
        <a href="/#faq">FAQ</a>
        <a href="/download/">Download</a>
        <a href="/blog/">Blog</a>
      </div>
      <button class="nav-toggle" aria-label="Menu" aria-expanded="false">
        <span></span><span></span><span></span>
      </button>
      <div class="nav-actions">
        <a href="https://github.com/immurok" target="_blank" rel="noopener" class="btn btn-outline btn-sm btn-icon" aria-label="GitHub" title="GitHub">
          <svg aria-hidden="true" width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
        </a>
        <a href="https://discord.gg/beavzPCanZ" target="_blank" rel="noopener" class="btn btn-outline btn-sm btn-icon" aria-label="Discord" title="Discord">
          <svg aria-hidden="true" width="18" height="18" fill="currentColor" viewBox="0 0 24 24"><path d="M20.317 4.37a19.79 19.79 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.74 19.74 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028c.462-.63.874-1.295 1.226-1.994a.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/></svg>
        </a>
        <a href="https://checkout.immurok.com/account" class="btn btn-primary btn-sm">My Order</a>
      </div>
    </div>
  </nav>'''

# One footer for the whole site. index.html, download/, the language pages and
# the blog theme carry the same columns; the homepage adds a Languages column.
FOOTER_COLS = '''        <div class="footer-col">
          <h4>Product</h4>
          <a href="/#features">Features</a>
          <a href="/ik-1/">Buy IK-1</a>
          <a href="/ik-1/#specs">Specs</a>
          <a href="/download/">Download</a>
          <a href="/changelog/">Changelog</a>
          <a href="/blog/">Blog</a>
        </div>
        <div class="footer-col">
          <h4>Use cases</h4>
          <a href="/mac-mini/">Mac mini &amp; desktop Macs</a>
          <a href="/windows/">Windows</a>
          <a href="/linux/">Linux</a>
          <a href="/ai-agents/">AI coding agents</a>
          <a href="/vs/touch-id/">vs Touch ID</a>
          <a href="/vs/yubikey/">vs YubiKey</a>
        </div>
        <div class="footer-col">
          <h4>Company</h4>
          <a href="/about/">About</a>
          <a href="/contact/">Contact</a>
          <a href="https://discord.gg/beavzPCanZ" target="_blank" rel="noopener">Discord</a>
          <a href="https://github.com/immurok" target="_blank" rel="noopener">GitHub</a>
          <a href="https://mariadb.com/bsl11/" target="_blank" rel="noopener">License</a>
        </div>
        <div class="footer-col">
          <h4>Support</h4>
          <a href="https://checkout.immurok.com/account">Order status</a>
          <a href="https://checkout.immurok.com/policies/shipping-policy">Shipping policy</a>
          <a href="https://checkout.immurok.com/policies/refund-policy">Refund policy</a>
          <a href="https://checkout.immurok.com/policies/privacy-policy">Privacy policy</a>
          <a href="https://checkout.immurok.com/policies/terms-of-service">Terms of service</a>
        </div>'''

FOOTER = '''  <footer class="footer">
    <div class="footer-inner">
      <div class="footer-brand">
        <img class="footer-logo" src="/img/figma/logo-wordmark.png" width="187" height="34" alt="immurok">
        <p class="footer-tagline">Wireless fingerprint authentication for Mac, Windows &amp; Linux.</p>
        <!-- Email is assembled by main.js (setupObfuscatedEmail); the raw
             HTML never contains the address. Parts are reversed. -->
        <a class="footer-email" data-eu="olleh" data-ed="moc.korummi" rel="nofollow">Email us</a>
      </div>
      <nav class="footer-links" aria-label="Footer">
%s
      </nav>
    </div>
    <div class="footer-bottom">
      <span>&copy; %d immurok &middot; Nervina Next Pte. Ltd. (UEN 202128549C) &middot; 24 Sin Ming Lane, #06-97, Midview City, Singapore 573970</span>
      <span>Apps: Apache 2.0 &middot; Firmware: BSL 1.1</span>
    </div>
  </footer>''' % (FOOTER_COLS, datetime.date.today().year)

# The order panel shop.js drives. Same markup as index.html, absolute paths.
ORDER_DRAWER = '''  <div class="order-backdrop" hidden></div>
  <aside class="order-drawer" role="dialog" aria-modal="true" aria-labelledby="order-title" aria-hidden="true" hidden>
    <div class="order-head">
      <h3 id="order-title">Your order</h3>
      <button type="button" class="order-close" aria-label="Close">&times;</button>
    </div>
    <div class="order-item">
      <img class="order-item-img" src="/img/device-thumb-144.webp" width="72" height="72" alt="">
      <div class="order-item-text">
        <strong>immurok IK-1</strong>
        <span class="order-item-variant">Silver &middot; Pre-order</span>
      </div>
      <span class="order-item-price">US$69</span>
    </div>
    <div class="buy-form"
               data-item-name="immurok IK-1"
               data-shop-domain="erjmi0-6n.myshopify.com"
               data-shop-token="ec294bcc4cc8fc98614bdc690e7dcee6"
               data-checkout-domain="checkout.immurok.com"
               data-shop-id="gid://shopify/Shop/96194724127"
               data-form-location="product-page"
               data-price="69">
      <div class="order-qty" aria-label="Quantity">
        <span class="order-qty-label">Quantity</span>
        <div class="qty-stepper">
          <button type="button" class="qty-btn qty-minus" aria-label="Decrease quantity">&minus;</button>
          <output class="qty-value" aria-live="polite">1</output>
          <button type="button" class="qty-btn qty-plus" aria-label="Increase quantity">+</button>
        </div>
      </div>
      <select name="variant" aria-label="Color" hidden>
        <option value="gid://shopify/ProductVariant/52879802499359">Silver</option>
      </select>
      <select name="qty" aria-label="Quantity" hidden>
        <option>1</option><option>2</option><option>3</option><option>4</option><option>5</option>
      </select>
      <div class="buy-row">
        <label class="buy-field">
          <span>Ship to</span>
          <select name="country" aria-label="Ship to country" aria-describedby="buy-country-hint">
            <option value="">Select country</option>
          </select>
        </label>
      </div>
      <p class="buy-country-hint" id="buy-country-hint">Choose the country your order will ship to, and use the same country for your shipping address at checkout. Shipping, taxes and customs details depend on it.</p>
      <div class="buy-taxid" hidden>
        <label class="buy-field">
          <span class="buy-taxid-label"></span>
          <input type="text" name="taxid" autocomplete="off" spellcheck="false" maxlength="40">
        </label>
        <p class="buy-taxid-hint"></p>
        <p class="buy-taxid-error" role="alert" hidden></p>
      </div>
      <dl class="order-summary">
        <div><dt>Subtotal</dt><dd class="order-subtotal">US$69</dd></div>
        <div><dt>Shipping</dt><dd class="order-shipping">Calculated at checkout</dd></div>
        <div class="order-total-row"><dt>Total</dt><dd class="order-total">US$69</dd></div>
      </dl>
      <div class="buy-shipping" hidden></div>
      <a class="btn btn-primary btn-cta buy-btn" href="https://checkout.immurok.com/cart/52879802499359:1" rel="noopener">Continue to checkout</a>
      <p class="buy-note">Pre-order. Ships December 2026.</p>
    </div>
  </aside>'''


def shipping():
    """Countries from js/shipping-data.js, the cheapest tracked option each."""
    src = open(os.path.join(ROOT, 'js', 'shipping-data.js'), encoding='utf-8').read()
    data = json.loads(src[src.index('{'):src.rstrip().rstrip(';').rindex('}') + 1])
    out = {}
    for code, c in data['countries'].items():
        opts = [o for o in c['options'] if o.get('kind') == 'tracked'] or c['options']
        # Flat-rate options carry `usd`; tiered ones (tax included) carry
        # `tiers`, whose first entry is the single-unit price.
        price = lambda o: o['usd'] if 'usd' in o else o['tiers'][0]['usd']
        best = min(opts, key=price)
        out[code] = (price(best), tuple(best['eta']))
    return out


def product_node():
    ship = shipping()
    groups = {}
    for code, key in sorted(ship.items()):
        groups.setdefault(key, []).append(code)
    details = []
    for (usd, eta), codes in sorted(groups.items()):
        details.append({
            "@type": "OfferShippingDetails",
            "shippingRate": {"@type": "MonetaryAmount", "value": usd, "currency": "USD"},
            "shippingDestination": [{"@type": "DefinedRegion", "addressCountry": c} for c in codes],
            "deliveryTime": {
                "@type": "ShippingDeliveryTime",
                "transitTime": {"@type": "QuantitativeValue", "minValue": eta[0], "maxValue": eta[1], "unitCode": "DAY"},
            },
        })
    return {
        "@type": "Product",
        "@id": SITE + "/ik-1/#product",
        "name": "immurok IK-1",
        "alternateName": "immurok wireless fingerprint key",
        "description": ("A standalone wireless fingerprint key for desktop computers. One touch unlocks the screen, "
                        "approves sudo and admin prompts, signs SSH and Git commits, unlocks 1Password and Bitwarden and "
                        "releases TOTP codes on macOS, Windows and Linux. Fingerprints are stored and matched on the "
                        "device; no cloud and no account."),
        "brand": {"@id": SITE + "/#org"},
        "manufacturer": {"@id": SITE + "/#org"},
        "image": [SITE + p for p in PRODUCT_IMAGES],
        "url": SITE + "/ik-1/",
        "category": "Security key / biometric authenticator",
        "sku": "IK1-SILVER",
        "mpn": "IK-1",
        "gtin14": "00884400414250",
        "color": "Silver",
        "material": "Anodized aluminium",
        "weight": {"@type": "QuantitativeValue", "value": 40, "unitCode": "GRM"},
        "width": {"@type": "QuantitativeValue", "value": 44, "unitCode": "MMT"},
        "depth": {"@type": "QuantitativeValue", "value": 44, "unitCode": "MMT"},
        "height": {"@type": "QuantitativeValue", "value": 14.2, "unitCode": "MMT"},
        "countryOfOrigin": "CN",
        "additionalProperty": [
            {"@type": "PropertyValue", "name": "Supported operating systems",
             "value": "macOS 13.0 or later (Apple Silicon and Intel), Windows 10 and 11 (x64 and Arm64), Linux (Ubuntu, Fedora, Arch, Debian and most other distributions)"},
            {"@type": "PropertyValue", "name": "Connectivity", "value": "Bluetooth LE; pairs with up to 2 computers"},
            {"@type": "PropertyValue", "name": "Sensor", "value": "Capacitive fingerprint sensor, under 500 ms match"},
            {"@type": "PropertyValue", "name": "Battery", "value": "110 mAh LiPo, USB-C charging, 1+ month per charge"},
            {"@type": "PropertyValue", "name": "Subscription required", "value": "No"},
            {"@type": "PropertyValue", "name": "Cloud account required", "value": "No"},
            {"@type": "PropertyValue", "name": "Warranty", "value": "One-year limited warranty"},
        ],
        "offers": {
            "@type": "Offer",
            "@id": SITE + "/ik-1/#offer",
            "url": SITE + "/ik-1/",
            "availability": "https://schema.org/PreOrder",
            "availabilityStarts": "2026-12-01",
            "priceCurrency": "USD",
            "price": "69",
            "priceValidUntil": "2027-09-14",
            "itemCondition": "https://schema.org/NewCondition",
            "seller": {"@id": SITE + "/#org"},
            "shippingDetails": details,
            "hasMerchantReturnPolicy": {
                "@type": "MerchantReturnPolicy",
                "applicableCountry": sorted(ship),
                "returnPolicyCategory": "https://schema.org/MerchantReturnFiniteReturnWindow",
                "merchantReturnDays": 7,
                "returnMethod": "https://schema.org/ReturnByMail",
                "returnFees": "https://schema.org/FreeReturn",
                "refundType": "https://schema.org/FullRefund",
                "merchantReturnLink": "https://checkout.immurok.com/policies/refund-policy",
            },
        },
        "isRelatedTo": {"@id": SITE + "/#app"},
    }


ENTITIES = {'&ldquo;': '"', '&rdquo;': '"', '&amp;': '&', '&nbsp;': ' ',
            '&middot;': '·', '&ndash;': '–', '&mdash;': '—', '&rsquo;': "'", '&lsquo;': "'",
            '&times;': '×', '&rarr;': '→'}


def norm(fragment):
    text = re.sub(r'<[^>]+>', ' ', fragment)
    for k, v in ENTITIES.items():
        text = text.replace(k, v)
    return re.sub(r'\s+', ' ', html.unescape(text)).strip()


def faq_pairs(body):
    return [(norm(q), norm(a)) for q, a in
            re.findall(r'<details class="faq-item">\s*<summary>(.*?)</summary>\s*<p>(.*?)</p>\s*</details>', body, re.S)]


def load(name):
    text = open(os.path.join(PAGES_DIR, name), encoding='utf-8').read()
    m = re.match(r'\s*<!--meta\s*(\{.*?\})\s*-->\s*', text, re.S)
    if not m:
        raise SystemExit('%s: missing <!--meta {...} --> header' % name)
    meta = json.loads(m.group(1))
    for k in ('path', 'title', 'description'):
        if k not in meta:
            raise SystemExit('%s: meta.%s is required' % (name, k))
    return meta, text[m.end():].rstrip() + '\n'


def jsonld(meta, body):
    url = SITE + meta['path']
    crumbs = [("immurok", SITE + "/")] + [(n, SITE + p) for n, p in meta.get('crumbs', [])]
    crumbs.append((meta.get('crumb', meta['title'].split(':')[0].split(' | ')[0]), url))
    graph = [ORG, {
        "@type": meta.get('type', 'WebPage'),
        "@id": url + "#webpage",
        "url": url,
        "name": meta['title'],
        "description": meta['description'],
        "inLanguage": "en",
        "isPartOf": {"@id": SITE + "/#site"},
        "about": {"@id": SITE + "/ik-1/#product"},
        "primaryImageOfPage": {"@type": "ImageObject", "url": meta.get('og_image', OG_IMAGE)},
    }, {
        "@type": "BreadcrumbList",
        "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u}
                            for i, (n, u) in enumerate(crumbs)],
    }]
    pairs = faq_pairs(body)
    if pairs:
        graph.append({
            "@type": "FAQPage",
            "@id": url + "#faq",
            "url": url,
            "inLanguage": "en",
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in pairs],
        })
    if meta.get('product'):
        graph.append(product_node())
    doc = {"@context": "https://schema.org", "@graph": graph}
    return '\n'.join('  ' + line for line in json.dumps(doc, ensure_ascii=False, indent=2).split('\n'))


def render(meta, body):
    e = html.escape
    url = SITE + meta['path']
    og = meta.get('og_image', OG_IMAGE)
    scripts = ['  <script src="/js/main.js"></script>']
    extra = ''
    if meta.get('shop'):
        scripts = ['  <script src="/js/main.js"></script>',
                   '  <script src="/js/shipping-data.js"></script>',
                   '  <script src="/js/shop.js"></script>']
        extra = ORDER_DRAWER + '\n'
    scripts += ['  <script src="%s"></script>' % html.escape(src) for src in meta.get('scripts', [])]
    robots = '  <meta name="robots" content="noindex, nofollow">\n' if meta.get('noindex') else ''
    return '''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <!-- Analytics + consent (shared with every page; see js/analytics.js). -->
  <script src="/js/analytics.js"></script>

  <title>{title}</title>
  <meta name="description" content="{desc}">
  <link rel="canonical" href="{url}">
{robots}  <meta name="theme-color" content="#1bed43">

  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{desc}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{url}">
  <meta property="og:site_name" content="immurok">
  <meta property="og:image" content="{og}">
  <meta property="og:locale" content="en_US">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:site" content="@immurok_dev">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{desc}">
  <meta name="twitter:image" content="{og}">

  <link rel="icon" href="/favicon.ico" sizes="any">
  <link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
  <link rel="icon" type="image/png" sizes="16x16" href="/favicon-16.png">
  <link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">

  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="{fonts}" rel="stylesheet">
  <link rel="stylesheet" href="/css/style.css">

  <!-- Generated by tools/build-pages.py from tools/pages/{name}. Edit the
       fragment, not this file. -->
  <script type="application/ld+json">
{jsonld}
  </script>
</head>
<body>

  <a href="#main-content" class="skip-nav">Skip to content</a>

{nav}

  <main id="main-content">
{body}  </main>

{footer}

{scripts}
{extra}</body>
</html>
'''.format(title=e(meta['title']), desc=e(meta['description']), url=url, og=og,
           fonts=FONTS, name=meta['_name'], jsonld=jsonld(meta, body), nav=NAV,
           body=body, footer=FOOTER, scripts='\n'.join(scripts), extra=extra, robots=robots)


def pages():
    for name in sorted(os.listdir(PAGES_DIR)):
        if not name.endswith('.html'):
            continue
        meta, body = load(name)
        meta['_name'] = name
        yield meta, body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    stale = []
    for meta, body in pages():
        out = os.path.join(ROOT, meta['path'].strip('/'), 'index.html')
        new = render(meta, body)
        current = open(out, encoding='utf-8').read() if os.path.exists(out) else None
        if args.check:
            if current != new:
                stale.append(meta['path'])
            continue
        if current != new:
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, 'w', encoding='utf-8') as f:
                f.write(new)
            print('wrote %s' % meta['path'])
    if args.check:
        if stale:
            print('stale pages: %s' % ', '.join(stale), file=sys.stderr)
            return 1
        print('all generated pages up to date')
    return 0


if __name__ == '__main__':
    sys.exit(main())
