const test = require('node:test');
const assert = require('node:assert/strict');
const shop = require('../js/shop.js');

const GID = 'gid://shopify/ProductVariant/45678901234';

test('variantNumericId strips the gid prefix', () => {
  assert.equal(shop.variantNumericId(GID), '45678901234');
  assert.equal(shop.variantNumericId('45678901234'), '45678901234');
});

test('permalinkUrl builds a Shopify cart permalink', () => {
  assert.equal(shop.permalinkUrl('checkout.immurok.com', GID, 2),
    'https://checkout.immurok.com/cart/45678901234:2');
});

test('permalinkUrl clamps quantity to 1..10 integers', () => {
  assert.equal(shop.permalinkUrl('checkout.immurok.com', GID, 0).endsWith(':1'), true);
  assert.equal(shop.permalinkUrl('checkout.immurok.com', GID, 99).endsWith(':10'), true);
  assert.equal(shop.permalinkUrl('checkout.immurok.com', GID, 'abc').endsWith(':1'), true);
});

test('cartCreateRequest targets the Storefront API with the public token', () => {
  const { url, init } = shop.cartCreateRequest('immurok.myshopify.com', 'tok', GID, 3);
  assert.equal(url, 'https://immurok.myshopify.com/api/2025-07/graphql.json');
  assert.equal(init.method, 'POST');
  assert.equal(init.headers['X-Shopify-Storefront-Access-Token'], 'tok');
  const body = JSON.parse(init.body);
  assert.match(body.query, /cartCreate/);
  assert.deepEqual(body.variables.lines, [{ merchandiseId: GID, quantity: 3 }]);
});

test('checkoutUrlFromResponse reads the url and rejects userErrors', () => {
  assert.equal(shop.checkoutUrlFromResponse({
    data: { cartCreate: { cart: { checkoutUrl: 'https://checkout.immurok.com/c/abc' }, userErrors: [] } },
  }), 'https://checkout.immurok.com/c/abc');
  assert.equal(shop.checkoutUrlFromResponse({
    data: { cartCreate: { cart: null, userErrors: [{ message: 'nope' }] } },
  }), null);
  assert.equal(shop.checkoutUrlFromResponse({ errors: [{ message: 'bad token' }] }), null);
  assert.equal(shop.checkoutUrlFromResponse(null), null);
});

const withUrl = (url) => ({ data: { cartCreate: { cart: { checkoutUrl: url }, userErrors: [] } } });

test('checkoutUrlFromResponse pins the host when a checkout domain is given', () => {
  assert.equal(shop.checkoutUrlFromResponse(withUrl('https://checkout.immurok.com/c/abc'), 'checkout.immurok.com'),
    'https://checkout.immurok.com/c/abc');
  assert.equal(shop.checkoutUrlFromResponse(withUrl('https://immurok.myshopify.com/c/abc'), 'checkout.immurok.com'),
    'https://immurok.myshopify.com/c/abc');
  assert.equal(shop.checkoutUrlFromResponse(withUrl('https://evil.example/c/abc'), 'checkout.immurok.com'), null);
  assert.equal(shop.checkoutUrlFromResponse(withUrl('https://checkout.immurok.com.evil.test/c/abc'), 'checkout.immurok.com'), null);
});

const cfg = { shopDomain: 'immurok.myshopify.com', token: 'tok', checkoutDomain: 'checkout.immurok.com' };

test('createCheckout falls back to the permalink when the API returns an off-site url', async () => {
  const fetchImpl = async () => ({ ok: true, json: async () => withUrl('https://evil.example/c/abc') });
  assert.equal(await shop.createCheckout(fetchImpl, cfg, GID, 1),
    'https://checkout.immurok.com/cart/45678901234:1');
});

test('createCheckout returns the cart checkoutUrl on success', async () => {
  const fetchImpl = async () => ({
    ok: true,
    json: async () => ({ data: { cartCreate: { cart: { checkoutUrl: 'https://checkout.immurok.com/c/ok' }, userErrors: [] } } }),
  });
  assert.equal(await shop.createCheckout(fetchImpl, cfg, GID, 1), 'https://checkout.immurok.com/c/ok');
});

test('createCheckout falls back to the permalink on network error', async () => {
  const fetchImpl = async () => { throw new Error('offline'); };
  assert.equal(await shop.createCheckout(fetchImpl, cfg, GID, 2),
    'https://checkout.immurok.com/cart/45678901234:2');
});

test('createCheckout falls back to the permalink on non-2xx', async () => {
  const fetchImpl = async () => ({ ok: false, status: 401, json: async () => ({}) });
  assert.equal(await shop.createCheckout(fetchImpl, cfg, GID, 1),
    'https://checkout.immurok.com/cart/45678901234:1');
});

test('createCheckout falls back to the permalink on timeout', async () => {
  const fetchImpl = () => new Promise(() => {});
  assert.equal(await shop.createCheckout(fetchImpl, cfg, GID, 1, 20),
    'https://checkout.immurok.com/cart/45678901234:1');
});

// Two halves so tools/check-no-placeholders.py does not flag this test file.
const PLACEHOLDER = 'REPLACE' + '_ME';

test('isPlaceholderConfig spots an unfilled shop config', () => {
  assert.equal(shop.isPlaceholderConfig({ shopDomain: PLACEHOLDER + '.myshopify.com', token: 'tok' }), true);
  assert.equal(shop.isPlaceholderConfig({ shopDomain: 'immurok.myshopify.com', token: PLACEHOLDER + '_STOREFRONT_TOKEN' }), true);
  assert.equal(shop.isPlaceholderConfig(cfg), false);
  assert.equal(shop.isPlaceholderConfig({}), false);
});

function fakeDoc(cookie) {
  const d = { cookie: cookie || '', title: 'immurok', referrer: '' };
  return d;
}

test('shopifyCookies reuses existing _shopify_y and _shopify_s', () => {
  const d = fakeDoc('_shopify_y=abc; _shopify_s=def');
  const c = shop.shopifyCookies(d, 'immurok.com', 0);
  assert.deepEqual(c, { y: 'abc', s: 'def' });
});

test('shopifyCookies creates both cookies on the parent domain when missing', () => {
  const writes = [];
  const d = fakeDoc('');
  Object.defineProperty(d, 'cookie', { get: () => '', set: (v) => writes.push(v) });
  const c = shop.shopifyCookies(d, 'immurok.com', 0);
  assert.match(c.y, /^[0-9a-f-]{36}$/);
  assert.match(c.s, /^[0-9a-f-]{36}$/);
  assert.equal(writes.length, 2);
  assert.match(writes[0], /^_shopify_y=.*; Domain=\.immurok\.com; Path=\/; Max-Age=31536000; SameSite=Lax; Secure$/);
  assert.match(writes[1], /^_shopify_s=.*; Domain=\.immurok\.com; Path=\/; Max-Age=1800; SameSite=Lax; Secure$/);
});

test('shopifyCookies omits Domain on localhost', () => {
  const writes = [];
  const d = fakeDoc('');
  Object.defineProperty(d, 'cookie', { get: () => '', set: (v) => writes.push(v) });
  shop.shopifyCookies(d, 'localhost', 0);
  assert.equal(writes[0].includes('Domain='), false);
});

test('pageViewPayload carries the headless page view schema', () => {
  const p = shop.pageViewPayload(
    { shopId: 'gid://shopify/Shop/1', currency: 'USD' },
    { y: 'Y', s: 'S' },
    { title: 'immurok', referrer: 'https://x.test/' },
    { userAgent: 'UA', language: 'en-US' },
    'https://immurok.com/'
  );
  assert.equal(p.events[0].schema_id, 'trekkie_storefront_page_view/1.4');
  const pl = p.events[0].payload;
  assert.equal(pl.shopId, 1);
  assert.equal(pl.uniqToken, 'Y');
  assert.equal(pl.visitToken, 'S');
  assert.equal(pl.currency, 'USD');
  assert.equal(pl.isPersistentCookie, true);
  assert.equal(pl.hasUserConsent, true);
  assert.equal(pl.pageType, 'home');
  assert.equal(pl.url, 'https://immurok.com/');
  assert.equal(pl.referrer, 'https://x.test/');
  assert.equal(pl.userAgent, 'UA');
  assert.equal(pl.microSessionId.length, 36);
});

// ── Shipping / duties / tax id (shipping-data.js shape) ──────────────────────

const US = { name: 'United States', taxIncluded: false,
  options: [{ kind: 'tracked', code: 'S5561', eta: [5, 9], usd: 6.9 }],
  duties: { mode: 'ddu', vat: 0, duty: 0.375, threshold_usd: 0, threshold_basis: 'goods', fixed_fee_usd: 0 } };
const KR = { name: 'South Korea', taxIncluded: false,
  options: [{ kind: 'tracked', code: 'HW', eta: [5, 7], usd: 3.9 }],
  duties: { mode: 'ddu', vat: 0.10, duty: 0.08, threshold_usd: 150, threshold_basis: 'goods', fixed_fee_usd: 0,
            tax_id: { level: 'required', label: 'PCCC', pattern: '^P\\d{12}$', hint: 'h' } } };
const SA = { name: 'Saudi Arabia', taxIncluded: true,
  options: [{ kind: 'tracked', code: 'OH', eta: [6, 10], tiers: [{ qty: 1, usd: 25.9 }, { qty: 2, usd: 36.9 }] }],
  duties: { mode: 'included', vat: 0, duty: 0, threshold_usd: 0, threshold_basis: 'goods', fixed_fee_usd: 0,
            tax_id: { level: 'required', label: 'Iqama', pattern: '^[12]\\d{9}$', hint: 'h' } } };
const GB = { name: 'United Kingdom', taxIncluded: false,
  options: [{ kind: 'tracked', code: 'SE007', eta: [3, 5], usd: 5.9 }, { kind: 'priority', code: 'PY', eta: [1, 2], usd: 9.9 }],
  duties: { mode: 'ddu', vat: 0.20, duty: 0, threshold_usd: 0, threshold_basis: 'goods+shipping', fixed_fee_usd: 10.5 } };

test('shippingSummary picks flat price or the tier for the quantity', () => {
  assert.deepEqual(shop.shippingSummary(US, 3).options, [{ kind: 'tracked', label: 'Tracked · 5–9 business days', usd: 6.9, eta: [5, 9] }]);
  assert.equal(shop.shippingSummary(SA, 2).options[0].usd, 36.9);
  assert.equal(shop.shippingSummary(SA, 9).options[0].usd, 36.9);   // beyond the last tier: last tier
  assert.equal(shop.shippingSummary(GB, 1).options.length, 2);
  assert.equal(shop.shippingSummary(null, 1), null);
});

test('estimateImportCharges follows mode, threshold and basis', () => {
  assert.deepEqual(shop.estimateImportCharges(US, 69, 6.9), { mode: 'ddu', usd: 25.88 });          // 69*0.375
  assert.deepEqual(shop.estimateImportCharges(KR, 69, 3.9), { mode: 'none', usd: 0 });             // under 150
  assert.deepEqual(shop.estimateImportCharges(KR, 207, 3.9), { mode: 'ddu', usd: 37.26 });         // 3 units: 207*0.18
  assert.deepEqual(shop.estimateImportCharges(GB, 69, 5.9), { mode: 'ddu', usd: 25.48 });          // (69+5.9)*0.2+10.5
  assert.deepEqual(shop.estimateImportCharges(SA, 69, 25.9), { mode: 'included', usd: 0 });
  assert.deepEqual(shop.estimateImportCharges({ options: [] }, 69, 0), { mode: 'unknown', usd: 0 });
});

test('validateTaxId enforces pattern only where required', () => {
  assert.deepEqual(shop.validateTaxId(KR, ''), { ok: false, level: 'required', message: 'PCCC is required for delivery to South Korea.' });
  assert.deepEqual(shop.validateTaxId(KR, 'P123456789012'), { ok: true, level: 'required', message: '' });
  assert.equal(shop.validateTaxId(KR, 'p123456789012').ok, false);
  assert.deepEqual(shop.validateTaxId(US, ''), { ok: true, level: null, message: '' });
  const opt = { name: 'X', options: [], duties: { mode: 'ddu', tax_id: { level: 'optional', label: 'ID', pattern: '^.{5,40}$', hint: '' } } };
  assert.equal(shop.validateTaxId(opt, '').ok, true);
  assert.equal(shop.validateTaxId(opt, 'abc').ok, false);
});

test('cartCreateRequest carries buyerIdentity and attributes when given', () => {
  const { init } = shop.cartCreateRequest('s.myshopify.com', 'tok', GID, 1,
    { countryCode: 'KR', attributes: [{ key: 'Tax ID', value: 'P123456789012' }] });
  const body = JSON.parse(init.body);
  assert.deepEqual(body.variables.buyerIdentity, { countryCode: 'KR' });
  assert.deepEqual(body.variables.attributes, [{ key: 'Tax ID', value: 'P123456789012' }]);
  assert.match(body.query, /buyerIdentity: \$buyerIdentity/);
  const plain = JSON.parse(shop.cartCreateRequest('s.myshopify.com', 'tok', GID, 1).init.body);
  assert.equal(plain.variables.buyerIdentity, undefined);
  assert.deepEqual(plain.variables.attributes, []);
});

test('permalinkUrl appends cart attributes as a query string', () => {
  assert.equal(shop.permalinkUrl('checkout.immurok.com', GID, 2, { 'Tax ID': 'P1 2', 'Ship to (site)': 'KR' }),
    'https://checkout.immurok.com/cart/45678901234:2?attributes%5BTax%20ID%5D=P1%202&attributes%5BShip%20to%20(site)%5D=KR');
  assert.equal(shop.permalinkUrl('checkout.immurok.com', GID, 2, {}), 'https://checkout.immurok.com/cart/45678901234:2');
});

test('guessCountry reads the region from a BCP47 tag', () => {
  const c = { US: US, KR: KR };
  assert.equal(shop.guessCountry('en-US', c), 'US');
  assert.equal(shop.guessCountry('ko-KR', c), 'KR');
  assert.equal(shop.guessCountry('de', c), '');
  assert.equal(shop.guessCountry('fr-FR', c), '');
});

test('orderTotals adds shipping only once a country is known', () => {
  assert.deepEqual(shop.orderTotals(69, 3, 6.9), { subtotal: 207, shipping: 6.9, total: 213.9 });
  assert.deepEqual(shop.orderTotals(69, 1, null), { subtotal: 69, shipping: null, total: 69 });
  assert.deepEqual(shop.orderTotals(69, 99, 0), { subtotal: 690, shipping: 0, total: 690 });   // qty clamps to 10
});

// ── GA4 ecommerce + cross-domain linker ─────────────────────────────────────

const SEL = { sku: 'IK1-SILVER', name: 'immurok IK-1', color: 'Silver', variant: GID, qty: 2, price: 69, country: 'DE' };

test('ecommerceParams builds a GA4 items payload with value = price × qty', () => {
  const p = shop.ecommerceParams(SEL);
  assert.equal(p.currency, 'USD');
  assert.equal(p.value, 138);
  assert.equal(p.shipping_country, 'DE');
  assert.deepEqual(p.items, [{ item_id: 'IK1-SILVER', item_name: 'immurok IK-1', item_variant: 'Silver', price: 69, quantity: 2 }]);
});

test('ecommerceParams falls back to the variant id when there is no sku, and omits an empty country', () => {
  const p = shop.ecommerceParams({ name: 'immurok IK-1', variant: GID, qty: 1, price: 69 });
  assert.equal(p.items[0].item_id, '45678901234');
  assert.equal(p.value, 69);
  assert.equal('shipping_country' in p, false);
});

test('metaEventFor maps GA4 ecommerce names to Meta standard events', () => {
  assert.equal(shop.metaEventFor('view_item'), 'ViewContent');
  assert.equal(shop.metaEventFor('add_to_cart'), 'AddToCart');
  assert.equal(shop.metaEventFor('begin_checkout'), 'InitiateCheckout');
  assert.equal(shop.metaEventFor('shipping_country_select'), null);
});

function linkerDoc(decorate) {
  const body = { appended: [], appendChild(el) { this.appended.push(el); el.parentNode = this; }, removeChild(el) { el.parentNode = null; } };
  return {
    body,
    createElement() {
      return { href: '', parentNode: null, style: {},
        dispatchEvent() { if (decorate) this.href = this.href + (this.href.indexOf('?') >= 0 ? '&' : '?') + '_gl=1*abc'; return true; } };
    },
  };
}

test('linkerDecorate returns the href after the gtag linker had a chance to decorate it', () => {
  const doc = linkerDoc(true);
  assert.equal(shop.linkerDecorate(doc, 'https://checkout.immurok.com/c/abc?key=1'),
    'https://checkout.immurok.com/c/abc?key=1&_gl=1*abc');
  assert.equal(doc.body.appended[0].parentNode, null, 'temporary anchor is removed');
});

test('linkerDecorate hands back the original url when nothing decorates it', () => {
  assert.equal(shop.linkerDecorate(linkerDoc(false), 'https://checkout.immurok.com/c/abc'), 'https://checkout.immurok.com/c/abc');
  assert.equal(shop.linkerDecorate(null, 'https://x.test/'), 'https://x.test/');
});
