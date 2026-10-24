// Shopify orders/create webhook -> GA4 Measurement Protocol purchase backfill.
//
// POST /api/shopify-order   (Shopify Admin -> Settings -> Notifications -> Webhooks)
//   -> 200 always once the signature checks out (Shopify retries anything else)
//   -> 401 bad / missing X-Shopify-Hmac-Sha256
//   -> 400 body is not JSON
//
// Why: the storefront is headless (immurok.com) and the checkout lives on
// checkout.immurok.com. The checkout tag only fires for buyers who accepted
// cookies and run no blocker, so GA4 saw ~56% of real orders (Sept/Oct 2026
// audit). shop.js writes the buyer's GA client_id / session_id into hidden
// cart attributes; this function replays every order as a `purchase` event
// from the server so GA4 counts and attributes all of them.
//
// Deduplication against the checkout tag: GA4 drops a purchase when the same
// user already sent one with the same transaction_id. We send the order under
// the buyer's own client_id with transaction_id = Shopify order id, so orders
// the browser tag already reported collapse into one. Orders with no client_id
// (consent declined / tag blocked) were never reported client-side; they go
// out under a synthetic, per-order client_id and are tagged cid_source =
// "synthetic" so the two populations can be separated in reports.
//
// Every event carries: backfill="webhook", cid_source="cookie"|"synthetic",
// order_country=<ISO-2 shipping country>. No buyer PII leaves this function.
//
// Env (Pages project settings -> Environment variables / Secrets):
//   SHOPIFY_WEBHOOK_SECRET  signing key shown at the bottom of the Webhooks
//                           section in Shopify Admin -> Settings -> Notifications
//   GA_MEASUREMENT_ID       e.g. "G-XXXXXXXXXX"   (shared with /api/t)
//   GA_API_SECRET           GA4 Measurement Protocol API secret (shared with /api/t)
//   LIKES                   KV binding (optional). Used for idempotency under
//                           the `ga_txn:` prefix so a Shopify redelivery does
//                           not send a second purchase.

const KV_PREFIX = "ga_txn:";
const KV_TTL = 60 * 60 * 24 * 7;
const MAX_BODY = 256 * 1024;

const enc = new TextEncoder();

function b64(bytes) {
  let s = "";
  for (const b of bytes) s += String.fromCharCode(b);
  return btoa(s);
}

function constantTimeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

// Shopify signs the raw request body with HMAC-SHA256 and sends it base64
// encoded in X-Shopify-Hmac-Sha256.
export async function verifyShopifyHmac(secret, rawBody, header) {
  if (!secret || typeof header !== "string" || !header) return false;
  const key = await crypto.subtle.importKey(
    "raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const sig = new Uint8Array(await crypto.subtle.sign("HMAC", key, enc.encode(rawBody)));
  return constantTimeEqual(b64(sig), header);
}

// shop.js stores the ids as hidden cart attributes (leading underscore), which
// Shopify carries onto the order as note_attributes.
export function gaIdsFromOrder(order) {
  const attrs = Array.isArray(order && order.note_attributes) ? order.note_attributes : [];
  const get = (name) => {
    const a = attrs.find((x) => x && x.name === name);
    return a && typeof a.value === "string" ? a.value : "";
  };
  return { clientId: get("_ga_client_id"), sessionId: get("_ga_session_id") };
}

// Stable per-order stand-in for a GA client id, shaped like the real thing
// (<random>.<timestamp>) so GA4 treats it as an ordinary user.
export async function syntheticClientId(orderId) {
  const digest = new Uint8Array(
    await crypto.subtle.digest("SHA-256", enc.encode("immurok-order:" + String(orderId))));
  let digits = "";
  for (const b of digest) digits += String(b).padStart(3, "0");
  return digits.slice(0, 10) + "." + digits.slice(10, 20);
}

function num(v) {
  const n = parseFloat(v);
  return Number.isFinite(n) ? n : 0;
}

function orderCountry(order) {
  const ship = order.shipping_address && order.shipping_address.country_code;
  const bill = order.billing_address && order.billing_address.country_code;
  return String(ship || bill || "");
}

function items(order) {
  const lines = Array.isArray(order.line_items) ? order.line_items : [];
  return lines.map((li) => ({
    item_id: String(li.sku || ""),
    item_name: String(li.title || ""),
    item_variant: String(li.variant_title || ""),
    quantity: parseInt(li.quantity, 10) || 1,
    price: num(li.price),
  }));
}

export async function purchasePayload(order) {
  const ids = gaIdsFromOrder(order);
  const cookie = Boolean(ids.clientId);
  const clientId = cookie ? ids.clientId : await syntheticClientId(order.id);
  const shippingSet = order.total_shipping_price_set && order.total_shipping_price_set.shop_money;

  const params = {
    transaction_id: String(order.id),
    value: num(order.total_price),
    currency: String(order.currency || "USD"),
    tax: num(order.total_tax),
    shipping: num(shippingSet && shippingSet.amount),
    items: items(order),
    engagement_time_msec: 1,
    backfill: "webhook",
    cid_source: cookie ? "cookie" : "synthetic",
    order_country: orderCountry(order),
  };
  if (cookie && ids.sessionId) params.session_id = ids.sessionId;

  const payload = { client_id: clientId, events: [{ name: "purchase", params }] };
  const created = Date.parse(order.created_at);
  if (Number.isFinite(created)) payload.timestamp_micros = created * 1000;
  return payload;
}

async function alreadySent(env, orderId) {
  if (!env.LIKES) return false;
  try { return (await env.LIKES.get(KV_PREFIX + orderId)) !== null; } catch { return false; }
}

async function markSent(env, orderId) {
  if (!env.LIKES) return;
  try { await env.LIKES.put(KV_PREFIX + orderId, "1", { expirationTtl: KV_TTL }); } catch {}
}

export async function onRequestPost({ request, env }) {
  const raw = await request.text();
  if (raw.length > MAX_BODY) return new Response("too large", { status: 413 });

  const ok = await verifyShopifyHmac(
    env.SHOPIFY_WEBHOOK_SECRET, raw, request.headers.get("X-Shopify-Hmac-Sha256"));
  if (!ok) return new Response("bad signature", { status: 401 });

  if (request.headers.get("X-Shopify-Topic") !== "orders/create") {
    return new Response("ignored", { status: 200 });
  }

  let order;
  try { order = JSON.parse(raw); } catch { return new Response("bad json", { status: 400 }); }
  if (!order || order.id === undefined || order.id === null) {
    return new Response("bad payload", { status: 400 });
  }
  if (order.test === true) return new Response("test order", { status: 200 });

  if (await alreadySent(env, order.id)) return new Response("duplicate", { status: 200 });

  // Mark first: a retried delivery racing with a slow GA call must not send twice.
  await markSent(env, order.id);

  if (env.GA_MEASUREMENT_ID && env.GA_API_SECRET) {
    const url = "https://www.google-analytics.com/mp/collect" +
      `?measurement_id=${env.GA_MEASUREMENT_ID}&api_secret=${env.GA_API_SECRET}`;
    const payload = await purchasePayload(order);
    try {
      await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (e) {
      console.log(`shopify-order: GA send failed for ${order.id}: ${e && e.message}`);
    }
  } else {
    console.log("shopify-order: GA_MEASUREMENT_ID / GA_API_SECRET not configured");
  }

  return new Response("ok", { status: 200 });
}
// Non-POST methods get an automatic 405 from Pages (only onRequestPost is defined).
