// Tests for functions/api/shopify-order.js: Shopify orders/create webhook ->
// GA4 Measurement Protocol purchase backfill.
const test = require('node:test');
const assert = require('node:assert/strict');
const { createHmac } = require('node:crypto');

const SECRET = 'whsec_test';
const MP_URL_RE = /^https:\/\/www\.google-analytics\.com\/mp\/collect\?measurement_id=G-TEST&api_secret=mp_secret$/;

function order(overrides) {
  return Object.assign({
    id: 7001,
    name: '#1381',
    test: false,
    currency: 'USD',
    total_price: '75.90',
    total_tax: '0.00',
    total_shipping_price_set: { shop_money: { amount: '6.90', currency_code: 'USD' } },
    created_at: '2026-10-08T03:08:00Z',
    line_items: [
      { sku: 'IK1-SILVER', title: 'immurok IK-1', variant_title: 'Silver', quantity: 1, price: '69.00', product_id: 1, variant_id: 11 },
    ],
    note_attributes: [
      { name: 'Ship to (site)', value: 'US' },
      { name: '_ga_client_id', value: '1234567890.1700000000' },
      { name: '_ga_session_id', value: '1759900000' },
    ],
    shipping_address: { country_code: 'US' },
    billing_address: { country_code: 'JP' },
    email: 'buyer@example.com',
  }, overrides || {});
}

function sign(body, secret) {
  return createHmac('sha256', secret).update(body).digest('base64');
}

// Fake KV with the subset of the Workers KV API the function uses.
function fakeKv() {
  const store = new Map();
  return {
    store,
    get: async (k) => (store.has(k) ? store.get(k) : null),
    put: async (k, v) => { store.set(k, v); },
  };
}

function makeEnv(kv) {
  return {
    SHOPIFY_WEBHOOK_SECRET: SECRET,
    GA_MEASUREMENT_ID: 'G-TEST',
    GA_API_SECRET: 'mp_secret',
    LIKES: kv || fakeKv(),
  };
}

// Captures fetch calls; returns the list.
function stubFetch(t, status = 204) {
  const calls = [];
  const orig = globalThis.fetch;
  globalThis.fetch = async (url, init) => {
    calls.push({ url: String(url), body: JSON.parse(init.body) });
    return new Response(null, { status });
  };
  t.after(() => { globalThis.fetch = orig; });
  return calls;
}

async function post(mod, env, body, headers) {
  const request = new Request('https://immurok.com/api/shopify-order', {
    method: 'POST',
    headers: Object.assign({
      'Content-Type': 'application/json',
      'X-Shopify-Topic': 'orders/create',
      'X-Shopify-Hmac-Sha256': sign(body, SECRET),
    }, headers || {}),
    body,
  });
  return mod.onRequestPost({ request, env });
}

let mod;
test.before(async () => { mod = await import('../functions/api/shopify-order.js'); });

test('verifyShopifyHmac accepts a matching signature and rejects a wrong one', async () => {
  const body = '{"id":1}';
  assert.equal(await mod.verifyShopifyHmac(SECRET, body, sign(body, SECRET)), true);
  assert.equal(await mod.verifyShopifyHmac(SECRET, body, sign(body, 'other')), false);
  assert.equal(await mod.verifyShopifyHmac(SECRET, body, ''), false);
  assert.equal(await mod.verifyShopifyHmac(SECRET, body, null), false);
});

test('gaIdsFromOrder reads the hidden cart attributes', () => {
  assert.deepEqual(mod.gaIdsFromOrder(order()), {
    clientId: '1234567890.1700000000', sessionId: '1759900000',
  });
  assert.deepEqual(mod.gaIdsFromOrder(order({ note_attributes: [] })), { clientId: '', sessionId: '' });
  assert.deepEqual(mod.gaIdsFromOrder(order({ note_attributes: null })), { clientId: '', sessionId: '' });
});

test('syntheticClientId is stable per order and shaped like a GA client id', async () => {
  const a = await mod.syntheticClientId(7001);
  const b = await mod.syntheticClientId(7001);
  const c = await mod.syntheticClientId(7002);
  assert.equal(a, b);
  assert.notEqual(a, c);
  assert.match(a, /^\d{10}\.\d{10}$/);
});

test('purchasePayload uses the cookie client id and session when present', async () => {
  const p = await mod.purchasePayload(order());
  assert.equal(p.client_id, '1234567890.1700000000');
  assert.equal(p.timestamp_micros, Date.parse('2026-10-08T03:08:00Z') * 1000);
  assert.equal(p.events.length, 1);
  const ev = p.events[0];
  assert.equal(ev.name, 'purchase');
  assert.equal(ev.params.transaction_id, '7001');
  assert.equal(ev.params.value, 75.9);
  assert.equal(ev.params.currency, 'USD');
  assert.equal(ev.params.tax, 0);
  assert.equal(ev.params.shipping, 6.9);
  assert.equal(ev.params.session_id, '1759900000');
  assert.equal(ev.params.engagement_time_msec, 1);
  assert.equal(ev.params.backfill, 'webhook');
  assert.equal(ev.params.cid_source, 'cookie');
  assert.equal(ev.params.order_country, 'US');
  assert.deepEqual(ev.params.items, [
    { item_id: 'IK1-SILVER', item_name: 'immurok IK-1', item_variant: 'Silver', quantity: 1, price: 69 },
  ]);
});

test('purchasePayload falls back to a synthetic client id and says so', async () => {
  const p = await mod.purchasePayload(order({ note_attributes: [{ name: 'Ship to (site)', value: 'DE' }], shipping_address: { country_code: 'DE' } }));
  assert.equal(p.client_id, await mod.syntheticClientId(7001));
  const ev = p.events[0];
  assert.equal(ev.params.cid_source, 'synthetic');
  assert.equal(ev.params.order_country, 'DE');
  assert.equal('session_id' in ev.params, false);
});

test('purchasePayload never carries buyer PII', async () => {
  const text = JSON.stringify(await mod.purchasePayload(order()));
  assert.equal(text.includes('buyer@example.com'), false);
  assert.equal(text.includes('shipping_address'), false);
});

test('purchasePayload falls back to billing country and tolerates missing fields', async () => {
  const p = await mod.purchasePayload(order({
    shipping_address: null, total_shipping_price_set: undefined, total_tax: undefined, line_items: [{ title: 'x', quantity: 2, price: '1.50' }],
  }));
  const ev = p.events[0];
  assert.equal(ev.params.order_country, 'JP');
  assert.equal(ev.params.shipping, 0);
  assert.equal(ev.params.tax, 0);
  assert.deepEqual(ev.params.items, [{ item_id: '', item_name: 'x', item_variant: '', quantity: 2, price: 1.5 }]);
});

test('rejects a request with a bad signature and sends nothing', async (t) => {
  const calls = stubFetch(t);
  const res = await post(mod, makeEnv(), JSON.stringify(order()), { 'X-Shopify-Hmac-Sha256': 'nope' });
  assert.equal(res.status, 401);
  assert.equal(calls.length, 0);
});

test('rejects when the secret is not configured', async (t) => {
  const calls = stubFetch(t);
  const env = makeEnv(); delete env.SHOPIFY_WEBHOOK_SECRET;
  const res = await post(mod, env, JSON.stringify(order()));
  assert.equal(res.status, 401);
  assert.equal(calls.length, 0);
});

test('forwards a signed order to the Measurement Protocol and returns 200', async (t) => {
  const calls = stubFetch(t);
  const res = await post(mod, makeEnv(), JSON.stringify(order()));
  assert.equal(res.status, 200);
  assert.equal(calls.length, 1);
  assert.match(calls[0].url, MP_URL_RE);
  assert.equal(calls[0].body.client_id, '1234567890.1700000000');
  assert.equal(calls[0].body.events[0].params.transaction_id, '7001');
});

test('skips test orders but still returns 200', async (t) => {
  const calls = stubFetch(t);
  const res = await post(mod, makeEnv(), JSON.stringify(order({ test: true })));
  assert.equal(res.status, 200);
  assert.equal(calls.length, 0);
});

test('ignores topics other than orders/create', async (t) => {
  const calls = stubFetch(t);
  const res = await post(mod, makeEnv(), JSON.stringify(order()), { 'X-Shopify-Topic': 'orders/updated' });
  assert.equal(res.status, 200);
  assert.equal(calls.length, 0);
});

test('sends each order once even when Shopify redelivers', async (t) => {
  const calls = stubFetch(t);
  const kv = fakeKv();
  const env = makeEnv(kv);
  const body = JSON.stringify(order());
  assert.equal((await post(mod, env, body)).status, 200);
  assert.equal((await post(mod, env, body)).status, 200);
  assert.equal(calls.length, 1);
  assert.equal(kv.store.has('ga_txn:7001'), true);
});

test('still forwards when no KV binding is available', async (t) => {
  const calls = stubFetch(t);
  const env = makeEnv(); delete env.LIKES;
  const res = await post(mod, env, JSON.stringify(order()));
  assert.equal(res.status, 200);
  assert.equal(calls.length, 1);
});

test('returns 200 even when GA is unreachable', async (t) => {
  const orig = globalThis.fetch;
  globalThis.fetch = async () => { throw new Error('network down'); };
  t.after(() => { globalThis.fetch = orig; });
  const res = await post(mod, makeEnv(), JSON.stringify(order()));
  assert.equal(res.status, 200);
});

test('rejects malformed JSON after a valid signature', async (t) => {
  const calls = stubFetch(t);
  const res = await post(mod, makeEnv(), '{not json');
  assert.equal(res.status, 400);
  assert.equal(calls.length, 0);
});
