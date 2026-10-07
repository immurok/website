const test = require('node:test');
const assert = require('node:assert/strict');
const ks = require('../js/ks-shipping.js');

const GID = 'gid://shopify/ProductVariant/52991571624223';
const CFG = { shopDomain: 'erjmi0-6n.myshopify.com', token: 'tok', checkoutDomain: 'checkout.immurok.com', variant: GID };

test('validateBackerNumber accepts a positive integer, with or without a leading #', () => {
  assert.deepEqual(ks.validateBackerNumber('1234'), { ok: true, value: '1234' });
  assert.deepEqual(ks.validateBackerNumber(' #1234 '), { ok: true, value: '1234' });
  assert.deepEqual(ks.validateBackerNumber('1'), { ok: true, value: '1' });
});

test('validateBackerNumber rejects anything that is not a plain positive integer', () => {
  for (const bad of ['', '   ', '0', '007', '12a', '12.5', '-3', '1 2', '１２３', '1234567890123']) {
    assert.equal(ks.validateBackerNumber(bad).ok, false, JSON.stringify(bad));
  }
});

test('validateEmail needs one @ and a dot in the domain', () => {
  assert.equal(ks.validateEmail('a@b.co'), true);
  assert.equal(ks.validateEmail('  a@b.co  '), true);
  assert.equal(ks.validateEmail(''), false);
  assert.equal(ks.validateEmail('a@b'), false);
  assert.equal(ks.validateEmail('a b@c.d'), false);
  assert.equal(ks.validateEmail('@c.d'), false);
});

test('clampAmount keeps the amount an integer in 1..500', () => {
  assert.equal(ks.clampAmount('10'), 10);
  assert.equal(ks.clampAmount(10), 10);
  assert.equal(ks.clampAmount('2.9'), 2);
  assert.equal(ks.clampAmount('0'), 1);
  assert.equal(ks.clampAmount('abc'), 1);
  assert.equal(ks.clampAmount(''), 1);
  assert.equal(ks.clampAmount(1000), 500);
});

test('permalinkUrl carries amount, backer number and email', () => {
  assert.equal(ks.permalinkUrl('checkout.immurok.com', GID, 10, { backer: '1234', email: 'a@b.co' }),
    'https://checkout.immurok.com/cart/52991571624223:10?attributes%5BBacker%20Number%5D=1234&checkout%5Bemail%5D=a%40b.co');
  assert.equal(ks.permalinkUrl('checkout.immurok.com', GID, 3),
    'https://checkout.immurok.com/cart/52991571624223:3');
});

test('cartCreateRequest sends one line, the backer attribute and the buyer email', () => {
  const { url, init } = ks.cartCreateRequest(CFG, 10, { backer: '1234', email: 'a@b.co' });
  assert.equal(url, 'https://erjmi0-6n.myshopify.com/api/2026-07/graphql.json');
  assert.equal(init.method, 'POST');
  assert.equal(init.headers['X-Shopify-Storefront-Access-Token'], 'tok');
  const body = JSON.parse(init.body);
  assert.match(body.query, /cartCreate/);
  assert.deepEqual(body.variables.lines, [{ merchandiseId: GID, quantity: 10 }]);
  assert.deepEqual(body.variables.attributes, [{ key: 'Backer Number', value: '1234' }]);
  assert.deepEqual(body.variables.buyerIdentity, { email: 'a@b.co' });
});

test('checkoutUrlFromResponse only accepts our checkout domain', () => {
  const ok = { data: { cartCreate: { cart: { checkoutUrl: 'https://checkout.immurok.com/cn/abc' }, userErrors: [] } } };
  assert.equal(ks.checkoutUrlFromResponse(ok, 'checkout.immurok.com'), 'https://checkout.immurok.com/cn/abc');
  const other = { data: { cartCreate: { cart: { checkoutUrl: 'https://evil.example/x' }, userErrors: [] } } };
  assert.equal(ks.checkoutUrlFromResponse(other, 'checkout.immurok.com'), null);
  const err = { data: { cartCreate: { cart: null, userErrors: [{ message: 'nope' }] } } };
  assert.equal(ks.checkoutUrlFromResponse(err, 'checkout.immurok.com'), null);
  assert.equal(ks.checkoutUrlFromResponse({}, 'checkout.immurok.com'), null);
});

test('createCheckout resolves the API checkout URL on success', async () => {
  const fetchImpl = async () => ({ ok: true, json: async () => ({ data: { cartCreate: { cart: { checkoutUrl: 'https://checkout.immurok.com/cn/abc' }, userErrors: [] } } }) });
  assert.equal(await ks.createCheckout(fetchImpl, CFG, 10, { backer: '1234', email: 'a@b.co' }, 1000),
    'https://checkout.immurok.com/cn/abc');
});

test('createCheckout falls back to the permalink on HTTP error, user error or timeout', async () => {
  const fallback = 'https://checkout.immurok.com/cart/52991571624223:10?attributes%5BBacker%20Number%5D=1234&checkout%5Bemail%5D=a%40b.co';
  const fields = { backer: '1234', email: 'a@b.co' };
  assert.equal(await ks.createCheckout(async () => ({ ok: false, status: 500 }), CFG, 10, fields, 1000), fallback);
  assert.equal(await ks.createCheckout(async () => { throw new Error('net'); }, CFG, 10, fields, 1000), fallback);
  const slow = () => new Promise(() => {});
  assert.equal(await ks.createCheckout(slow, CFG, 10, fields, 20), fallback);
  const userErr = async () => ({ ok: true, json: async () => ({ data: { cartCreate: { cart: null, userErrors: [{ message: 'x' }] } } }) });
  assert.equal(await ks.createCheckout(userErr, CFG, 10, fields, 1000), fallback);
});

test('money formats whole dollars without cents', () => {
  assert.equal(ks.money(1), 'US$1');
  assert.equal(ks.money(10), 'US$10');
  assert.equal(ks.money(2.5), 'US$2.50');
});
