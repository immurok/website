//
// Buy button for the pricing block. The page holds the price and the variant
// list in HTML; this script only turns "Buy now" into a Shopify checkout.
//
//   1. Reads the config from data-* attributes on the .buy-form element.
//   2. On click, calls Storefront API cartCreate and redirects to checkoutUrl.
//   2b. If shipping-data.js is loaded, shows a Ship to select with the
//      shipping price, an import-charge estimate and, where customs needs
//      one, a tax-id field; country and tax id ride along in the cart.
//   3. On any failure (network, bad token, timeout) redirects to the cart
//      permalink https://<checkout-domain>/cart/<variant>:<qty>, which needs
//      no JS at all. The button's href is kept in sync with the selects so the
//      permalink also works with JS disabled.
//
// Pure helpers are exported for node --test (website/tests/shop.test.js).

(function (root, factory) {
  var api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) {
    root.ikShop = api;
    if (root.document) {
      if (root.document.readyState === 'loading') {
        root.document.addEventListener('DOMContentLoaded', function () { api.setupBuyForms(root.document); api.setupGallery(root.document); api.setupOrderDrawer(root.document); api.setupViewItem(root.document); });
      } else {
        api.setupBuyForms(root.document);
        api.setupGallery(root.document);
        api.setupOrderDrawer(root.document);
        api.setupViewItem(root.document);
      }
    }
  }
})(typeof window !== 'undefined' ? window : null, function () {
  'use strict';

  var API_VERSION = '2025-07';
  // Safety clamp for hand-typed permalinks (/cart/<variant>:<qty>). The
  // visible quantity select offers 1-5 on purpose; this is only the ceiling.
  var MAX_QTY = 10;

  function clampQty(qty) {
    var n = parseInt(qty, 10);
    if (!(n >= 1)) return 1;
    return n > MAX_QTY ? MAX_QTY : n;
  }

  function round2(x) { return Math.round(x * 100) / 100; }

  function variantNumericId(gid) {
    var s = String(gid || '');
    var i = s.lastIndexOf('/');
    return i >= 0 ? s.slice(i + 1) : s;
  }

  // attributes (optional object) become Shopify cart attributes on the
  // permalink: /cart/<variant>:<qty>?attributes[Tax ID]=...
  function permalinkUrl(checkoutDomain, variantGid, qty, attributes) {
    var url = 'https://' + checkoutDomain + '/cart/' + variantNumericId(variantGid) + ':' + clampQty(qty);
    var parts = [];
    Object.keys(attributes || {}).forEach(function (k) {
      if (attributes[k]) parts.push(encodeURIComponent('attributes[' + k + ']') + '=' + encodeURIComponent(attributes[k]));
    });
    return parts.length ? url + '?' + parts.join('&') : url;
  }

  var CART_CREATE = 'mutation CartCreate($lines: [CartLineInput!]!, $attributes: [AttributeInput!], $buyerIdentity: CartBuyerIdentityInput) {' +
    ' cartCreate(input: {lines: $lines, attributes: $attributes, buyerIdentity: $buyerIdentity}) {' +
    '  cart { checkoutUrl }' +
    '  userErrors { message }' +
    ' }' +
    '}';

  // extra: { countryCode: 'KR', attributes: [{key, value}] }, both optional.
  // countryCode preselects the checkout country (and market); attributes land
  // on the order as "Additional details" for the ERP and customs paperwork.
  function cartCreateRequest(shopDomain, token, variantGid, qty, extra) {
    var variables = { lines: [{ merchandiseId: variantGid, quantity: clampQty(qty) }], attributes: (extra && extra.attributes) || [] };
    if (extra && extra.countryCode) variables.buyerIdentity = { countryCode: extra.countryCode };
    return {
      url: 'https://' + shopDomain + '/api/' + API_VERSION + '/graphql.json',
      init: {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Shopify-Storefront-Access-Token': token,
        },
        body: JSON.stringify({ query: CART_CREATE, variables: variables }),
      },
    };
  }

  // checkoutDomain is optional; when given, the URL we are about to navigate
  // to must belong to our own checkout domain or to a myshopify.com store, so
  // a tampered or mistaken API response cannot redirect a buyer off-site.
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

  function createCheckout(fetchImpl, cfg, variantGid, qty, timeoutMs, extra) {
    var fallback = permalinkUrl(cfg.checkoutDomain, variantGid, qty, extra && extra.permalinkAttributes);
    var req = cartCreateRequest(cfg.shopDomain, cfg.token, variantGid, qty, extra);
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

  // ── Shipping, import charges, tax ids ──────────────────────────────────
  // `country` is one entry of window.ikShipping.countries (built by
  // shop/rates from the 4PX price sheet + duties.json). Pure, for tests.

  function optionPrice(o, qty) {
    if (typeof o.usd === 'number') return o.usd;
    var tiers = o.tiers || [];
    var hit = null;
    for (var i = 0; i < tiers.length; i++) if (tiers[i].qty <= qty) hit = tiers[i];
    return hit ? hit.usd : (tiers[0] ? tiers[0].usd : 0);
  }

  function shippingSummary(country, qty) {
    if (!country || !country.options) return null;
    var q = clampQty(qty);
    return { options: country.options.map(function (o) {
      return { kind: o.kind,
               label: (o.kind === 'priority' ? 'Priority' : 'Tracked') + ' · ' + o.eta[0] + '–' + o.eta[1] + ' business days',
               usd: optionPrice(o, q), eta: o.eta };
    }) };
  }

  function estimateImportCharges(country, goodsUsd, shippingUsd) {
    var d = country && country.duties;
    if (!d) return { mode: 'unknown', usd: 0 };
    if (d.mode === 'included') return { mode: 'included', usd: 0 };
    if (d.mode === 'none') return { mode: 'none', usd: 0 };
    var base = d.threshold_basis === 'goods+shipping' ? goodsUsd + shippingUsd : goodsUsd;
    if (d.threshold_usd && base <= d.threshold_usd) return { mode: 'none', usd: 0 };
    return { mode: 'ddu', usd: round2(base * ((d.vat || 0) + (d.duty || 0)) + (d.fixed_fee_usd || 0)) };
  }

  function validateTaxId(country, value) {
    var t = country && country.duties && country.duties.tax_id;
    if (!t) return { ok: true, level: null, message: '' };
    var v = String(value || '').trim();
    if (!v) {
      return t.level === 'required'
        ? { ok: false, level: 'required', message: t.label + ' is required for delivery to ' + country.name + '.' }
        : { ok: true, level: 'optional', message: '' };
    }
    var ok = new RegExp(t.pattern).test(v);
    return { ok: ok, level: t.level, message: ok ? '' : 'Please check the ' + t.label + ' format.' };
  }

  function guessCountry(lang, countries) {
    var m = /^[a-z]{2,3}-([A-Z]{2})\b/.exec(String(lang || ''));
    return m && countries[m[1]] ? m[1] : '';
  }

  // shippingUsd null = country not chosen yet.
  function orderTotals(price, qty, shippingUsd) {
    var q = clampQty(qty);
    var subtotal = round2(price * q);
    var shipping = typeof shippingUsd === 'number' ? round2(shippingUsd) : null;
    return { subtotal: subtotal, shipping: shipping, total: shipping === null ? subtotal : round2(subtotal + shipping) };
  }

  function money(x) { return 'US$' + (Math.round(x * 100) / 100).toFixed(2).replace(/\.00$/, ''); }

  // ── Analytics ──────────────────────────────────────────────────────────
  // The funnel uses GA4's standard ecommerce names (view_item → add_to_cart →
  // begin_checkout) so the built-in reports and Google Ads imports work
  // without mapping. purchase is not fired here: it happens on the Shopify
  // checkout domain and reaches GA4 / Meta through Shopify's channel apps.

  var META_EVENTS = { view_item: 'ViewContent', add_to_cart: 'AddToCart', begin_checkout: 'InitiateCheckout' };

  function metaEventFor(name) { return META_EVENTS[name] || null; }

  // sel: { sku, name, color, variant (gid), qty, price, country }
  function ecommerceParams(sel) {
    var q = clampQty(sel.qty);
    var item = { item_id: sel.sku || variantNumericId(sel.variant), item_name: sel.name, price: sel.price, quantity: q };
    if (sel.color) item.item_variant = sel.color;
    var p = { currency: 'USD', value: round2(sel.price * q), items: [item] };
    if (sel.country) p.shipping_country = sel.country;
    return p;
  }

  function track(name, params) {
    try { if (typeof window.ikTrack === 'function') window.ikTrack(name, params); } catch (e) {}
    try {
      var meta = metaEventFor(name);
      if (meta && typeof window.fbq === 'function') {
        var item = (params.items && params.items[0]) || {};
        window.fbq('track', meta, { content_type: 'product', content_ids: [item.item_id], content_name: item.item_name,
                                    num_items: item.quantity, value: params.value, currency: params.currency });
      }
    } catch (e) {}
  }

  // GA4's cross-domain linker only decorates links the visitor clicks. The
  // checkout URL comes back from the API and is navigated to by script, so
  // give the linker an anchor to decorate: it listens for mousedown on <a>
  // and rewrites href with _gl before navigation. Anything goes wrong, the
  // original URL is used; attribution is never allowed to block a purchase.
  function linkerDecorate(doc, url) {
    try {
      if (!doc || !doc.body) return url;
      var a = doc.createElement('a');
      a.href = url;
      a.style.display = 'none';
      doc.body.appendChild(a);
      var ev;
      try { ev = new MouseEvent('mousedown', { bubbles: true, cancelable: true }); }
      catch (e) { ev = { type: 'mousedown', bubbles: true }; }
      a.dispatchEvent(ev);
      var out = a.href || url;
      doc.body.removeChild(a);
      return out;
    } catch (e) {
      return url;
    }
  }

  function uuid() {
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
    var s = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx';
    return s.replace(/[xy]/g, function (c) {
      var r = Math.random() * 16 | 0;
      return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
  }

  function readCookie(doc, name) {
    var m = ('; ' + doc.cookie).match('; ' + name + '=([^;]*)');
    return m ? m[1] : '';
  }

  function writeCookie(doc, name, value, host, maxAge) {
    var domain = /\.[a-z]+$/i.test(host) && host.indexOf('.') > 0 ? '; Domain=.' + host.split('.').slice(-2).join('.') : '';
    doc.cookie = name + '=' + value + domain + '; Path=/; Max-Age=' + maxAge + '; SameSite=Lax; Secure';
  }

  // Shopify's storefront cookies: _shopify_y identifies the visitor for a
  // year, _shopify_s the session for 30 minutes. Set on the parent domain so
  // checkout.immurok.com sees the same values and Shopify Analytics can
  // attribute the order to this visit.
  function shopifyCookies(doc, host, now) {
    var y = readCookie(doc, '_shopify_y');
    var s = readCookie(doc, '_shopify_s');
    if (!y) { y = uuid(); writeCookie(doc, '_shopify_y', y, host, 31536000); }
    if (!s) { s = uuid(); writeCookie(doc, '_shopify_s', s, host, 1800); }
    return { y: y, s: s };
  }

  function pageViewPayload(cfg, cookies, doc, nav, url) {
    var shopIdNum = parseInt(variantNumericId(cfg.shopId), 10);
    var path = '';
    try { path = new URL(url).pathname; } catch (e) {}
    return {
      metadata: { event_sent_at_ms: Date.now() },
      events: [{
        schema_id: 'trekkie_storefront_page_view/1.4',
        payload: {
          shopId: shopIdNum,
          currency: cfg.currency || 'USD',
          uniqToken: cookies.y,
          visitToken: cookies.s,
          microSessionId: uuid(),
          microSessionCount: 1,
          isPersistentCookie: true,
          hasUserConsent: true,
          pageType: path === '/' ? 'home' : 'page',
          url: url,
          path: path,
          referrer: doc.referrer || '',
          title: doc.title || '',
          userAgent: nav.userAgent || '',
          navigationType: 'navigate',
          navigationApi: 'PerformanceNavigationTiming',
          shopifySalesChannel: 'headless',
          contentLanguage: nav.language || 'en',
        },
        metadata: { event_created_at_ms: Date.now() },
      }],
    };
  }

  function sendPageView(cfg) {
    if (!cfg.shopId) return;
    try {
      var cookies = shopifyCookies(document, window.location.hostname, Date.now());
      var payload = pageViewPayload(cfg, cookies, document, navigator, window.location.href);
      var body = JSON.stringify(payload);
      var url = 'https://monorail-edge.shopifysvc.com/unstable/produce_batch';
      if (navigator.sendBeacon) navigator.sendBeacon(url, new Blob([body], { type: 'text/plain' }));
      else fetch(url, { method: 'POST', body: body, keepalive: true, headers: { 'Content-Type': 'text/plain' } });
    } catch (e) {}
  }

  // The shop config is filled in by hand once the Shopify store exists. If a
  // build with the placeholders still in it ever reaches production, hide the
  // form: a missing Buy button is a visible bug, a Buy button that leads to a
  // broken checkout is a silent lost sale.
  // Spelled in two halves so website/tools/check-no-placeholders.py, which
  // refuses to sync any file carrying the marker, does not flag this file.
  var PLACEHOLDER = 'REPLACE' + '_ME';

  function isPlaceholderConfig(cfg) {
    return String(cfg.token || '').indexOf(PLACEHOLDER) === 0 ||
           String(cfg.shopDomain || '').indexOf(PLACEHOLDER) === 0;
  }

  // What the buyer currently has picked, read straight from the DOM so the
  // drawer and the pricing block can report it without sharing state.
  function currentSelection(doc) {
    var form = doc.querySelector('.buy-form');
    var swatch = doc.querySelector('.product-swatch input:checked');
    var variantSel = form && form.querySelector('select[name="variant"]');
    var qtySel = form && form.querySelector('select[name="qty"]');
    var countrySel = form && form.querySelector('select[name="country"]');
    return {
      sku: swatch ? swatch.getAttribute('data-sku') || '' : '',
      name: (form && form.getAttribute('data-item-name')) || 'immurok IK-1',
      color: swatch ? swatch.getAttribute('data-color') || '' : '',
      variant: variantSel ? variantSel.value : (swatch ? swatch.value : ''),
      qty: qtySel ? qtySel.value : 1,
      price: parseFloat((form && form.getAttribute('data-price')) || '0'),
      country: countrySel ? countrySel.value : '',
    };
  }

  // view_item once, when the pricing block first scrolls into view. Low
  // threshold on purpose: on phones the block is taller than the viewport,
  // so a 30% rule would never fire.
  function setupViewItem(doc) {
    var el = doc.getElementById('pricing');
    if (!el || typeof IntersectionObserver !== 'function') return;
    var io = new IntersectionObserver(function (entries) {
      if (!entries.some(function (e) { return e.isIntersecting; })) return;
      io.disconnect();
      track('view_item', ecommerceParams(currentSelection(doc)));
    }, { threshold: 0.1 });
    io.observe(el);
  }

  function setupBuyForms(doc) {
    var forms = doc.querySelectorAll('.buy-form');
    Array.prototype.forEach.call(forms, function (form) {
      var cfg = {
        shopDomain: form.getAttribute('data-shop-domain'),
        token: form.getAttribute('data-shop-token'),
        checkoutDomain: form.getAttribute('data-checkout-domain'),
      };
      if (isPlaceholderConfig(cfg)) { form.hidden = true; return; }
      var location = form.getAttribute('data-form-location') || 'pricing';
      var price = parseFloat(form.getAttribute('data-price') || '0');
      var variantSel = form.querySelector('select[name="variant"]');
      var qtySel = form.querySelector('select[name="qty"]');
      var btn = form.querySelector('a.buy-btn');
      if (!variantSel || !qtySel || !btn || !cfg.shopDomain || !cfg.checkoutDomain) return;

      var shipping = (typeof window !== 'undefined' && window.ikShipping && window.ikShipping.countries) || null;
      var countrySel = form.querySelector('select[name="country"]');
      var shipBox = form.querySelector('.buy-shipping');
      var taxWrap = form.querySelector('.buy-taxid');
      var taxInput = taxWrap ? taxWrap.querySelector('input') : null;
      var taxLabel = taxWrap ? taxWrap.querySelector('.buy-taxid-label') : null;
      var taxHint = taxWrap ? taxWrap.querySelector('.buy-taxid-hint') : null;
      var taxError = taxWrap ? taxWrap.querySelector('.buy-taxid-error') : null;
      // Only nag about a missing tax id once the buyer has touched the field
      // or tried to buy; the disabled button already signals it is needed.
      var taxTouched = false;
      var qtyMinus = form.querySelector('.qty-minus');
      var qtyPlus = form.querySelector('.qty-plus');
      var qtyValue = form.querySelector('.qty-value');
      var sumSubtotal = form.querySelector('.order-subtotal');
      var sumShipping = form.querySelector('.order-shipping');
      var sumTotal = form.querySelector('.order-total');
      var qtyMax = qtySel.options.length || MAX_QTY;

      if (shipping && countrySel) {
        var isos = Object.keys(shipping).sort(function (a, b) { return shipping[a].name.localeCompare(shipping[b].name); });
        isos.forEach(function (iso) {
          var opt = doc.createElement('option');
          opt.value = iso; opt.textContent = shipping[iso].name;
          countrySel.appendChild(opt);
        });
        countrySel.value = guessCountry(typeof navigator !== 'undefined' ? navigator.language : '', shipping);
      } else if (countrySel) {
        var wrap = countrySel.closest('.buy-row');
        if (wrap) wrap.hidden = true;
      }

      function countryObj() { return shipping && countrySel && countrySel.value ? shipping[countrySel.value] : null; }
      function current() {
        return { variant: variantSel.value, qty: clampQty(qtySel.value),
                 country: countrySel ? countrySel.value : '', taxId: taxInput ? taxInput.value.trim() : '' };
      }
      function attributesFor(c) {
        var a = {};
        var country = countryObj();
        if (c.country) a['Ship to (site)'] = c.country;
        if (c.taxId && country && country.duties && country.duties.tax_id) {
          a['Tax ID'] = c.taxId;
          a['Tax ID type'] = country.duties.tax_id.label;
        }
        return a;
      }
      function syncHref() {
        var c = current();
        btn.setAttribute('href', permalinkUrl(cfg.checkoutDomain, c.variant, c.qty, attributesFor(c)));
      }
      function render() {
        var c = current();
        var country = countryObj();
        if (qtyValue) qtyValue.textContent = String(c.qty);
        if (qtyMinus) qtyMinus.disabled = c.qty <= 1;
        if (qtyPlus) qtyPlus.disabled = c.qty >= qtyMax;
        if (sumSubtotal) {
          var firstShip = country ? shippingSummary(country, c.qty).options[0].usd : null;
          var t = orderTotals(price, c.qty, firstShip);
          sumSubtotal.textContent = money(t.subtotal);
          sumShipping.textContent = t.shipping === null ? 'Calculated at checkout' : money(t.shipping);
          sumTotal.textContent = money(t.total);
        }
        if (shipBox) {
          if (!country) {
            shipBox.hidden = true;
          } else {
            var s = shippingSummary(country, c.qty);
            var lines = s.options.map(function (o) {
              return '<div>Shipping <strong>' + money(o.usd) + '</strong> · ' + o.label + '</div>';
            });
            // Policy: say who pays, never guess how much. estimateImportCharges
            // stays available for internal checks but is not shown to buyers.
            if (country.taxIncluded) lines.push('<div>Import taxes included in shipping.</div>');
            else lines.push('<div class="buy-shipping-fine">Import duties, VAT and handling fees, if any, are charged by your local customs on delivery and are the recipient\'s responsibility.</div>');
            shipBox.innerHTML = lines.join('');
            shipBox.hidden = false;
          }
        }
        if (taxWrap && taxInput) {
          var t = country && country.duties && country.duties.tax_id;
          if (!t) {
            taxWrap.hidden = true;
            taxInput.value = '';
          } else {
            taxWrap.hidden = false;
            taxLabel.textContent = t.label + (t.level === 'required' ? '' : ' (optional)');
            taxInput.placeholder = t.placeholder || '';
            taxHint.textContent = t.hint || '';
          }
          var v = validateTaxId(country, taxInput.value.trim());
          var showError = !v.ok && (taxTouched || taxInput.value.trim() !== '');
          taxError.textContent = showError ? v.message : '';
          taxError.hidden = !showError;
          btn.classList.toggle('is-disabled', !v.ok);
          btn.setAttribute('aria-disabled', v.ok ? 'false' : 'true');
        }
        syncHref();
      }
      variantSel.addEventListener('change', render);
      qtySel.addEventListener('change', render);
      if (countrySel) countrySel.addEventListener('change', function () {
        track('shipping_country_select', { country: countrySel.value });
        render();
      });
      function bumpQty(delta) {
        var q = clampQty(qtySel.value) + delta;
        if (q < 1 || q > qtyMax) return;
        qtySel.value = String(q);
        render();
      }
      if (qtyMinus) qtyMinus.addEventListener('click', function () { bumpQty(-1); });
      if (qtyPlus) qtyPlus.addEventListener('click', function () { bumpQty(1); });
      if (taxInput) {
        taxInput.addEventListener('input', render);
        taxInput.addEventListener('blur', function () { taxTouched = true; render(); });
      }
      render();

      var analyticsCfg = { shopId: form.getAttribute('data-shop-id'), currency: 'USD' };
      if (window.ikConsentGranted) sendPageView(analyticsCfg);
      else doc.addEventListener('ik-consent-granted', function () { sendPageView(analyticsCfg); }, { once: true });

      btn.addEventListener('click', function (ev) {
        if (ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.button !== 0) return;
        ev.preventDefault();
        var c = current();
        if (!validateTaxId(countryObj(), c.taxId).ok) {
          taxTouched = true;
          render();
          if (taxInput) taxInput.focus();
          return;
        }
        var attrs = attributesFor(c);
        var extra = {
          countryCode: c.country || undefined,
          attributes: Object.keys(attrs).map(function (k) { return { key: k, value: attrs[k] }; }),
          permalinkAttributes: attrs,
        };
        // Anything that throws synchronously here (no fetch, a blocked
        // analytics global, a broken URL) must still get the buyer to
        // checkout, so fall back to the JS-free permalink.
        try {
          var sel = currentSelection(doc);
          sel.variant = c.variant; sel.qty = c.qty; sel.country = c.country; sel.price = price;
          var params = ecommerceParams(sel);
          params.form_location = location;
          track('begin_checkout', params);
          btn.classList.add('is-busy');
          btn.setAttribute('aria-busy', 'true');
          if (typeof window.fetch !== 'function') throw new Error('no fetch');
          createCheckout(window.fetch.bind(window), cfg, c.variant, c.qty, undefined, extra).then(function (url) {
            window.location.assign(linkerDecorate(doc, url));
          });
        } catch (e) {
          window.location.assign(permalinkUrl(cfg.checkoutDomain, c.variant, c.qty, attrs));
        }
      });
    });
  }

  // Product photo strip: thumbnails swap the stage image. The last thumb is
  // the interactive 3D model (3d/index.html, same origin); it loads on first
  // use and follows the chosen color through window.__setVariant.
  function setupGallery(doc) {
    var main = doc.getElementById('product-main');
    var frame = doc.getElementById('product-3d');
    var thumbs = doc.querySelectorAll('.product-thumb');
    if (!main || !thumbs.length) return;
    function currentVariant3d() {
      var checked = doc.querySelector('.product-swatch input:checked');
      return (checked && checked.getAttribute('data-3d')) || 'silver';
    }
    function apply3dVariant() {
      try {
        var w = frame && frame.contentWindow;
        if (w && typeof w.__setVariant === 'function') w.__setVariant(currentVariant3d());
      } catch (e) {}
    }
    function select(btn) {
      Array.prototype.forEach.call(thumbs, function (t) {
        var on = t === btn;
        t.classList.toggle('is-active', on);
        t.setAttribute('aria-selected', on ? 'true' : 'false');
      });
      if (btn.getAttribute('data-kind') === '3d' && frame) {
        if (!frame.getAttribute('src')) {
          frame.addEventListener('load', function () { setTimeout(apply3dVariant, 300); });
          frame.src = btn.getAttribute('data-src');
        } else {
          apply3dVariant();
        }
        main.hidden = true; frame.hidden = false;
        if (main.parentNode) main.parentNode.classList.add('is-3d');
        return;
      }
      if (frame) frame.hidden = true;
      if (main.parentNode) main.parentNode.classList.remove('is-3d');
      main.hidden = false;
      main.src = btn.getAttribute('data-src');
      main.srcset = btn.getAttribute('data-srcset') || '';
      main.alt = btn.getAttribute('data-alt') || '';
    }
    Array.prototype.forEach.call(thumbs, function (btn, i) {
      btn.addEventListener('click', function () { select(btn); });
      btn.addEventListener('keydown', function (ev) {
        if (ev.key !== 'ArrowRight' && ev.key !== 'ArrowLeft') return;
        var j = (i + (ev.key === 'ArrowRight' ? 1 : thumbs.length - 1)) % thumbs.length;
        thumbs[j].focus(); select(thumbs[j]); ev.preventDefault();
      });
    });
    var swatches = doc.querySelectorAll('.product-swatch input');
    Array.prototype.forEach.call(swatches, function (input) {
      input.addEventListener('change', function () {
        Array.prototype.forEach.call(swatches, function (o) { o.closest('.product-swatch').classList.toggle('is-active', o.checked); });
        var name = doc.querySelector('.product-color-name');
        if (name) name.textContent = input.getAttribute('data-color') || '';
        var variantSel = doc.querySelector('.buy-form select[name="variant"]');
        if (variantSel) { variantSel.value = input.value; variantSel.dispatchEvent(new Event('change')); }
        var v = doc.querySelector('.order-item-variant');
        if (v) v.textContent = (input.getAttribute('data-color') || '') + ' · Pre-order';
        apply3dVariant();
      });
    });
  }

  // Slide-in order panel. Opened by [data-open-order]; Esc, backdrop and the
  // close button shut it and hand focus back to the opener.
  function setupOrderDrawer(doc) {
    var drawer = doc.querySelector('.order-drawer');
    var backdrop = doc.querySelector('.order-backdrop');
    if (!drawer || !backdrop) return;
    var opener = null;
    function open(btn) {
      // An opener inside a menu is hidden by the time the drawer closes;
      // data-return-focus names the visible control to focus instead.
      var ret = btn && btn.getAttribute('data-return-focus');
      opener = (ret && doc.querySelector(ret)) || btn || null;
      drawer.hidden = false; backdrop.hidden = false;
      // next frame so the transition runs from the hidden state
      requestAnimationFrame(function () { drawer.classList.add('is-open'); backdrop.classList.add('is-open'); });
      drawer.setAttribute('aria-hidden', 'false');
      doc.body.classList.add('order-open');
      var first = drawer.querySelector('.order-close');
      if (first) first.focus();
      track('add_to_cart', ecommerceParams(currentSelection(doc)));
    }
    function close() {
      drawer.classList.remove('is-open'); backdrop.classList.remove('is-open');
      drawer.setAttribute('aria-hidden', 'true');
      doc.body.classList.remove('order-open');
      setTimeout(function () { drawer.hidden = true; backdrop.hidden = true; }, 300);
      if (opener) opener.focus();
    }
    Array.prototype.forEach.call(doc.querySelectorAll('[data-open-order]'), function (btn) {
      btn.addEventListener('click', function () { open(btn); });
    });
    var closeBtn = drawer.querySelector('.order-close');
    if (closeBtn) closeBtn.addEventListener('click', close);
    backdrop.addEventListener('click', close);
    doc.addEventListener('keydown', function (ev) { if (ev.key === 'Escape' && !drawer.hidden) close(); });
  }

  return {
    variantNumericId: variantNumericId,
    orderTotals: orderTotals,
    setupGallery: setupGallery,
    setupOrderDrawer: setupOrderDrawer,
    setupViewItem: setupViewItem,
    currentSelection: currentSelection,
    ecommerceParams: ecommerceParams,
    metaEventFor: metaEventFor,
    linkerDecorate: linkerDecorate,
    permalinkUrl: permalinkUrl,
    cartCreateRequest: cartCreateRequest,
    checkoutUrlFromResponse: checkoutUrlFromResponse,
    createCheckout: createCheckout,
    isPlaceholderConfig: isPlaceholderConfig,
    setupBuyForms: setupBuyForms,
    shippingSummary: shippingSummary,
    estimateImportCharges: estimateImportCharges,
    validateTaxId: validateTaxId,
    guessCountry: guessCountry,
    shopifyCookies: shopifyCookies,
    pageViewPayload: pageViewPayload,
  };
});
