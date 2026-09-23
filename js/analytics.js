/*
 * immurok site analytics bootstrap — the single source of truth.
 *
 * This file used to be copy-pasted inline into index.html and the Hugo theme
 * head partial, and /download/ never got a copy at all. That is why Search
 * Console showed 41 clicks on /download/ while GA4 showed zero users. Every
 * page now loads this one file instead, so a new page cannot silently fall
 * out of the reporting.
 *
 * Load it synchronously in <head>, before anything that calls gtag/fbq:
 *   <script src="/js/analytics.js"></script>
 *
 * What it does:
 *   1. Installs the gtag / fbq queue stubs so any later code can fire events
 *      immediately, whether or not consent has been given yet.
 *   2. Geo-gates the real trackers: loads freely outside EU/EEA/UK/CH, and
 *      inside shows a consent banner (built here, so no page can forget it)
 *      and only loads after Accept.
 *   3. Normalises page_location: ad click IDs and URL fragments are stripped
 *      so one page stays one row in the reports. utm_* is deliberately kept,
 *      GA4 needs it for source/medium attribution.
 *   4. Exposes window.ikTrack(name, params) — a consent-safe event helper.
 *   5. Google Consent Mode v2 (basic): EU visitors start with everything
 *      denied and the tags only load after "update granted". Google Ads
 *      refuses to attribute or model EEA conversions without these signals.
 *   6. Cross-domain linker for the Shopify checkout, and the Google Ads tag
 *      once AW_ID is filled in.
 */
(function () {
  var GA_ID = 'G-N8YY5HG63Y';
  var FB_PIXEL_ID = '28061587893441067';
  // Google Ads conversion ID (AW-xxxxxxxxx). Empty = no Ads tag. Purchase is
  // imported into Ads from GA4 (it fires on the Shopify checkout), so the
  // only site-side Ads events are the ones listed in AW_CONVERSIONS.
  var AW_ID = '';
  // GA4 event name → Ads conversion label, e.g. { begin_checkout: 'AbCdEfGh' }.
  // Left empty until the conversion actions exist in the Ads account.
  var AW_CONVERSIONS = {};
  // Sessions must survive the hop to the checkout domain, or every order shows
  // up in GA4 as a fresh "direct" visit. Shopify's Google channel accepts the
  // _gl parameter on the other side.
  var LINKER_DOMAINS = ['immurok.com', 'checkout.immurok.com', 'erjmi0-6n.myshopify.com'];

  // ── gtag / fbq stubs ──────────────────────────────────────────────────────

  window.dataLayer = window.dataLayer || [];
  function gtag() { dataLayer.push(arguments); }
  window.gtag = gtag;

  // Matches the official Meta snippet so fbq() can be called at any time and
  // the queue replays once the real script loads.
  !function (f, b, e, v, n, t, s) {
    if (f.fbq) return;
    n = f.fbq = function () { n.callMethod ? n.callMethod.apply(n, arguments) : n.queue.push(arguments); };
    if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = '2.0'; n.queue = [];
  }(window);

  /**
   * Fire a GA4 event. Safe to call before consent (queued, dropped on reject)
   * and safe on pages where the tracker never loads.
   */
  window.ikTrack = function (name, params) {
    try { gtag('event', name, params || {}); } catch (e) {}
    try {
      if (AW_ID && AW_CONVERSIONS[name]) {
        var p = params || {};
        gtag('event', 'conversion', { send_to: AW_ID + '/' + AW_CONVERSIONS[name], value: p.value, currency: p.currency || 'USD' });
      }
    } catch (e) {}
  };

  // ── Consent Mode v2 ───────────────────────────────────────────────────────

  var CONSENT_TYPES = ['ad_storage', 'ad_user_data', 'ad_personalization', 'analytics_storage'];

  function consentAll(state) {
    var c = {};
    CONSENT_TYPES.forEach(function (k) { c[k] = state; });
    return c;
  }

  // ── page_location normalisation ───────────────────────────────────────────

  // Click-ID parameters: every ad click carries a unique value, so leaving
  // them in page_location splits a single page across hundreds of report rows.
  // utm_* is NOT in this list on purpose — GA4 parses it for attribution.
  var CLICK_IDS = /^(fbclid|gclid|gbraid|wbraid|dclid|msclkid|ttclid|twclid|li_fat_id|igshid|igsh|mc_cid|mc_eid|yclid|rdt_cid|epik|s_kwcid|_ga|_gl|ref_src|ref_url)$/i;

  function normalisedLocation() {
    try {
      var u = new URL(window.location.href);
      var keys = [];
      u.searchParams.forEach(function (_v, k) { keys.push(k); });
      keys.forEach(function (k) { if (CLICK_IDS.test(k)) u.searchParams.delete(k); });
      // Fragments carry no page identity (/#pricing and /#faq are the same
      // page) but do create separate rows.
      u.hash = '';
      return u.href;
    } catch (e) {
      return window.location.href;
    }
  }

  // ── Tracker loading ───────────────────────────────────────────────────────

  function loadGtag() {
    if (window.__gaLoaded) return;
    window.__gaLoaded = true;
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA_ID;
    (document.head || document.documentElement).appendChild(s);
    gtag('js', new Date());
    gtag('set', 'linker', { domains: LINKER_DOMAINS, accept_incoming: true });
    gtag('config', GA_ID, {
      anonymize_ip: true,
      page_location: normalisedLocation()
    });
    if (AW_ID) gtag('config', AW_ID, { allow_enhanced_conversions: true });
  }

  function loadFbPixel() {
    if (window.__fbqLoaded) return;
    window.__fbqLoaded = true;
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://connect.facebook.net/en_US/fbevents.js';
    (document.head || document.documentElement).appendChild(s);
    fbq('init', FB_PIXEL_ID);
    fbq('track', 'PageView');
  }

  function loadTrackers() {
    gtag('consent', 'update', consentAll('granted'));
    loadGtag();
    loadFbPixel();
    // Let other scripts (js/shop.js analytics) know tracking is allowed.
    window.ikConsentGranted = true;
    try { document.dispatchEvent(new CustomEvent('ik-consent-granted')); } catch (e) {}
  }

  // ── Consent banner ────────────────────────────────────────────────────────

  // Built here rather than in page markup so that every page — including any
  // page added later — has one. Styles live in css/style.css (#cookie-banner).
  function buildBanner() {
    if (document.getElementById('cookie-banner')) {
      return document.getElementById('cookie-banner');
    }
    var banner = document.createElement('div');
    banner.id = 'cookie-banner';
    banner.setAttribute('role', 'dialog');
    banner.setAttribute('aria-label', 'Cookie consent');
    banner.hidden = true;

    var text = document.createElement('p');
    text.textContent = 'We use analytics cookies to understand how visitors use the site. ' +
                       'You can accept or reject. Your choice is remembered.';

    var actions = document.createElement('div');
    actions.className = 'cookie-banner-actions';

    var reject = document.createElement('button');
    reject.type = 'button';
    reject.id = 'cookie-reject';
    reject.textContent = 'Reject';
    reject.addEventListener('click', function () {
      try { localStorage.setItem('ik-consent', 'reject'); } catch (e) {}
      banner.hidden = true;
    });

    var accept = document.createElement('button');
    accept.type = 'button';
    accept.id = 'cookie-accept';
    accept.textContent = 'Accept';
    accept.addEventListener('click', function () {
      try { localStorage.setItem('ik-consent', 'accept'); } catch (e) {}
      loadTrackers();
      banner.hidden = true;
    });

    actions.appendChild(reject);
    actions.appendChild(accept);
    banner.appendChild(text);
    banner.appendChild(actions);

    (document.body || document.documentElement).appendChild(banner);
    return banner;
  }

  function showBanner() {
    if (document.body) {
      buildBanner().hidden = false;
    } else {
      document.addEventListener('DOMContentLoaded', function () {
        buildBanner().hidden = false;
      });
    }
  }

  // ── Geo gate ──────────────────────────────────────────────────────────────

  var EU = {
    AT: 1, BE: 1, BG: 1, HR: 1, CY: 1, CZ: 1, DK: 1, EE: 1, FI: 1, FR: 1, DE: 1,
    GR: 1, HU: 1, IE: 1, IT: 1, LV: 1, LT: 1, LU: 1, MT: 1, NL: 1, PL: 1, PT: 1,
    RO: 1, SK: 1, SI: 1, ES: 1, SE: 1, IS: 1, LI: 1, NO: 1, GB: 1, CH: 1
  };

  var stored = null;
  try { stored = localStorage.getItem('ik-consent'); } catch (e) {}
  if (stored === 'accept') { loadTrackers(); return; }
  // Denied by default until the visitor accepts (or geo says no banner is
  // needed). Must be queued before any config call; the stub queue keeps
  // the order once gtag.js loads.
  gtag('consent', 'default', consentAll('denied'));
  if (stored === 'reject') { return; }

  // No stored choice yet — check geo via Cloudflare's free trace endpoint.
  fetch('/cdn-cgi/trace')
    .then(function (r) { return r.text(); })
    .then(function (t) {
      var m = t.match(/loc=([A-Z]{2})/);
      if (m && EU[m[1]]) showBanner();
      else loadTrackers();
    })
    .catch(function () {
      // Trace failed (unlikely on CF Pages) — default to not tracking, and
      // let the visitor opt in.
      showBanner();
    });
})();
