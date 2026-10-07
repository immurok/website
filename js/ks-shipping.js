//
// Kickstarter shipping fee top-up (/ks-shipping/). One Shopify product at
// US$1 per unit; the backer sets the amount (= quantity) they were quoted,
// gives their backer number and email, and goes to checkout, where Shopify
// collects the shipping address (the product "requires shipping" and sits in
// a dedicated $0 delivery profile, so the address is captured but nothing is
// charged for it).
//
//   1. Reads the config from data-* attributes on the #ks-form element.
//   2. On submit, validates the fields, calls Storefront API cartCreate with
//      the amount as quantity, the backer number as a cart attribute (lands on
//      the order as "Additional details") and the email as buyerIdentity, then
//      redirects to checkoutUrl.
//   3. On any failure (network, bad token, timeout) redirects to the cart
//      permalink https://<checkout-domain>/cart/<variant>:<amount>?attributes[...]
//      which needs no JS at all.
//
// Pure helpers are exported for node --test (website/tests/ks-shipping.test.js).

(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) {
    root.ikKsShipping = api;
    if (root.document) {
      if (root.document.readyState === 'loading') {
        root.document.addEventListener('DOMContentLoaded', function () { api.setup(root.document); });
      } else {
        api.setup(root.document);
      }
    }
  }
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';

  var API_VERSION = '2026-07';
  var MAX_AMOUNT = 500;
  var ATTR_BACKER = 'Backer Number';

  // A Kickstarter backer number is a plain positive integer; "#1234" is how
  // Kickstarter prints it, so a leading # is tolerated. Leading zeros, signs,
  // decimals and full-width digits are not.
  function validateBackerNumber(raw) {
    var v = String(raw == null ? '' : raw).trim().replace(/^#/, '');
    if (!/^[1-9][0-9]{0,9}$/.test(v)) return { ok: false, value: v };
    return { ok: true, value: v };
  }

  function validateEmail(raw) {
    var v = String(raw == null ? '' : raw).trim();
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v);
  }

  function clampAmount(raw) {
    var n = parseInt(raw, 10);
    if (!(n >= 1)) return 1;
    return n > MAX_AMOUNT ? MAX_AMOUNT : n;
  }

  function money(x) { return 'US$' + (Math.round(x * 100) / 100).toFixed(2).replace(/\.00$/, ''); }

  function variantNumericId(gid) {
    var m = /\/(\d+)$/.exec(String(gid));
    return m ? m[1] : String(gid);
  }

  // fields: { backer, email }, both optional here (the form validates first).
  function permalinkUrl(checkoutDomain, variantGid, amount, fields) {
    var url = 'https://' + checkoutDomain + '/cart/' + variantNumericId(variantGid) + ':' + clampAmount(amount);
    var parts = [];
    if (fields && fields.backer) parts.push(encodeURIComponent('attributes[' + ATTR_BACKER + ']') + '=' + encodeURIComponent(fields.backer));
    if (fields && fields.email) parts.push(encodeURIComponent('checkout[email]') + '=' + encodeURIComponent(fields.email));
    return parts.length ? url + '?' + parts.join('&') : url;
  }

  var CART_CREATE = 'mutation CartCreate($lines: [CartLineInput!]!, $attributes: [AttributeInput!], $buyerIdentity: CartBuyerIdentityInput) {' +
    ' cartCreate(input: {lines: $lines, attributes: $attributes, buyerIdentity: $buyerIdentity}) {' +
    '  cart { checkoutUrl }' +
    '  userErrors { message }' +
    ' }' +
    '}';

  function cartCreateRequest(cfg, amount, fields) {
    var variables = {
      lines: [{ merchandiseId: cfg.variant, quantity: clampAmount(amount) }],
      attributes: fields && fields.backer ? [{ key: ATTR_BACKER, value: fields.backer }] : [],
    };
    if (fields && fields.email) variables.buyerIdentity = { email: fields.email };
    return {
      url: 'https://' + cfg.shopDomain + '/api/' + API_VERSION + '/graphql.json',
      init: {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Shopify-Storefront-Access-Token': cfg.token,
        },
        body: JSON.stringify({ query: CART_CREATE, variables: variables }),
      },
    };
  }

  // The URL we are about to navigate to must belong to our own checkout
  // domain or to a myshopify.com store, so a tampered or mistaken API
  // response cannot redirect a backer off-site.
  function checkoutUrlFromResponse(json, checkoutDomain) {
    try {
      var cc = json.data.cartCreate;
      if (cc.userErrors && cc.userErrors.length) return null;
      var url = cc.cart && cc.cart.checkoutUrl;
      if (typeof url !== 'string' || url.indexOf('https://') !== 0) return null;
      if (checkoutDomain) {
        var host = new URL(url).hostname;
        if (host !== checkoutDomain && !/\.myshopify\.com$/.test(host)) return null;
      }
      return url;
    } catch (e) {
      return null;
    }
  }

  function withTimeout(promise, ms) {
    return new Promise(function (resolve, reject) {
      var t = setTimeout(function () { reject(new Error('timeout')); }, ms);
      promise.then(function (v) { clearTimeout(t); resolve(v); },
                   function (e) { clearTimeout(t); reject(e); });
    });
  }

  function createCheckout(fetchImpl, cfg, amount, fields, timeoutMs) {
    var fallback = permalinkUrl(cfg.checkoutDomain, cfg.variant, amount, fields);
    var req = cartCreateRequest(cfg, amount, fields);
    var attempt = Promise.resolve()
      .then(function () { return fetchImpl(req.url, req.init); })
      .then(function (res) {
        if (!res || !res.ok) throw new Error('http ' + (res && res.status));
        return res.json();
      })
      .then(function (json) {
        return checkoutUrlFromResponse(json, cfg.checkoutDomain) || fallback;
      });
    return withTimeout(attempt, timeoutMs || 4000).catch(function () { return fallback; });
  }

  // ── DOM ─────────────────────────────────────────────────────────────────

  function setup(doc) {
    var form = doc.getElementById('ks-form');
    if (!form) return;
    var cfg = {
      shopDomain: form.getAttribute('data-shop-domain'),
      token: form.getAttribute('data-shop-token'),
      checkoutDomain: form.getAttribute('data-checkout-domain'),
      variant: form.getAttribute('data-variant'),
    };
    var price = parseFloat(form.getAttribute('data-price') || '1');
    // Field names double as the permalink parameters for the no-JS submit.
    var backerInput = form.querySelector('input[name="attributes[' + ATTR_BACKER + ']"]');
    var emailInput = form.querySelector('input[name="checkout[email]"]');
    var amountInput = form.querySelector('input[name="amount"]');
    var minus = form.querySelector('.qty-minus');
    var plus = form.querySelector('.qty-plus');
    var total = form.querySelector('.order-total');
    var btn = form.querySelector('.buy-btn');
    var errBacker = form.querySelector('.ks-error-backer');
    var errEmail = form.querySelector('.ks-error-email');
    if (!backerInput || !emailInput || !amountInput || !btn || !cfg.shopDomain || !cfg.checkoutDomain || !cfg.variant) return;

    function amount() { return clampAmount(amountInput.value); }
    function fields() {
      return { backer: validateBackerNumber(backerInput.value).value, email: emailInput.value.trim() };
    }
    function render() {
      var a = amount();
      if (total) total.textContent = money(a * price);
      if (minus) minus.disabled = a <= 1;
      if (plus) plus.disabled = a >= MAX_AMOUNT;
      // Keep the no-JS path (plain form submit) in step with the fields.
      form.setAttribute('action', permalinkUrl(cfg.checkoutDomain, cfg.variant, a, fields()));
    }
    function normaliseAmount() {
      amountInput.value = String(amount());
      render();
    }
    function bump(delta) {
      var a = amount() + delta;
      if (a < 1 || a > MAX_AMOUNT) return;
      amountInput.value = String(a);
      render();
    }
    if (minus) minus.addEventListener('click', function () { bump(-1); });
    if (plus) plus.addEventListener('click', function () { bump(1); });
    amountInput.addEventListener('input', render);
    amountInput.addEventListener('change', normaliseAmount);
    amountInput.addEventListener('blur', normaliseAmount);
    backerInput.addEventListener('input', function () { if (errBacker) errBacker.hidden = true; render(); });
    emailInput.addEventListener('input', function () { if (errEmail) errEmail.hidden = true; render(); });

    // With JS the submit goes through the Storefront API (amount, backer
    // number and email all on the cart); the permalink in `action` is only
    // the fallback.
    form.addEventListener('submit', function (ev) {
      ev.preventDefault();
      var b = validateBackerNumber(backerInput.value);
      var e = validateEmail(emailInput.value);
      if (errBacker) errBacker.hidden = b.ok;
      if (errEmail) errEmail.hidden = e;
      if (!b.ok) { backerInput.focus(); return; }
      if (!e) { emailInput.focus(); return; }
      var a = amount();
      amountInput.value = String(a);
      var f = { backer: b.value, email: emailInput.value.trim() };
      btn.classList.add('is-busy');
      btn.disabled = true;
      var fetchImpl = typeof window !== 'undefined' && window.fetch ? window.fetch.bind(window) : function () { return Promise.reject(new Error('no fetch')); };
      createCheckout(fetchImpl, cfg, a, f, 4000).then(function (url) {
        window.location.href = url;
      });
    });

    render();
  }

  return {
    validateBackerNumber: validateBackerNumber,
    validateEmail: validateEmail,
    clampAmount: clampAmount,
    money: money,
    variantNumericId: variantNumericId,
    permalinkUrl: permalinkUrl,
    cartCreateRequest: cartCreateRequest,
    checkoutUrlFromResponse: checkoutUrlFromResponse,
    createCheckout: createCheckout,
    setup: setup,
  };
});
