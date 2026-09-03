// Telemetry forwarder for the immurok macOS app firmware-update funnel.
//
// POST /api/t  body: {"client_id":"<uuid>","events":[{"name":"fw_...","params":{...}}]}
//   -> 204 (always, unless the request itself is malformed)
//
// Runs as a Cloudflare Pages Function (same mechanism as /api/like). Holds the
// GA4 Measurement Protocol secret server-side so it never ships in the app, and
// so mainland-China clients (blocked from google-analytics.com) can still report
// via immurok.com. Client IP / User-Agent are NOT forwarded to GA.
//
// These are app events, not website traffic. Measurement Protocol hits carry
// no page_location, so in GA4 they land on an empty path / "(not set)" and get
// mixed into the website's user and key-event counts. To keep the two apart:
//
//   * Preferred: point GA_MEASUREMENT_ID_APP / GA_API_SECRET_APP at a separate
//     GA4 data stream (or property) for the app. Website reports then never
//     see these hits at all.
//   * Fallback: when only the shared stream is configured, every forwarded
//     event is stamped with a synthetic page_location and client_source so it
//     shows up as one identifiable row instead of a blank one, and can be
//     excluded from website reports with a single filter.
//
// Env (Pages project settings -> Environment variables / Secrets):
//   GA_MEASUREMENT_ID      e.g. "G-XXXXXXXXXX"   (shared / website stream)
//   GA_API_SECRET          GA4 Measurement Protocol API secret
//   GA_MEASUREMENT_ID_APP  optional, dedicated app stream (preferred)
//   GA_API_SECRET_APP      optional, secret for that stream

// Synthetic path for app-originated hits (see the note above). Not a real URL.
const APP_PAGE_LOCATION = "https://app.immurok.invalid/macos/firmware-update";

const ALLOWED_EVENTS = new Set([
  "fw_check", "fw_prompt_shown", "fw_update_started", "fw_hop_done",
  "fw_update_success", "fw_update_failed", "fw_update_resumed",
]);

export async function onRequestPost({ request, env }) {
  let body;
  try {
    const text = await request.text();
    if (text.length > 4096) return new Response("too large", { status: 413 });
    body = JSON.parse(text);
  } catch {
    return new Response("bad json", { status: 400 });
  }

  const { client_id, events } = body || {};
  if (typeof client_id !== "string" || client_id.length > 64 ||
      !Array.isArray(events) || events.length === 0 || events.length > 10) {
    return new Response("bad payload", { status: 400 });
  }
  for (const ev of events) {
    if (!ALLOWED_EVENTS.has(ev && ev.name)) {
      return new Response("unknown event", { status: 400 });
    }
  }

  // Route to the dedicated app stream when one is configured, otherwise fall
  // back to the shared stream.
  const dedicated = Boolean(env.GA_MEASUREMENT_ID_APP && env.GA_API_SECRET_APP);
  const measurementId = dedicated ? env.GA_MEASUREMENT_ID_APP : env.GA_MEASUREMENT_ID;
  const apiSecret = dedicated ? env.GA_API_SECRET_APP : env.GA_API_SECRET;

  // Stamp every event so app hits are never indistinguishable from web traffic.
  // APP_PAGE_LOCATION is a synthetic, non-routable URL: it exists only to give
  // these hits a label in the page-path dimension instead of "(not set)".
  const stamped = events.map((ev) => ({
    name: ev.name,
    params: {
      ...(ev.params || {}),
      client_source: "macos_app",
      page_location: APP_PAGE_LOCATION,
      page_title: "immurok macOS app (firmware update)",
    },
  }));

  // Forward to GA4 Measurement Protocol. Fire-and-forget: GA failures must not
  // surface to the client. Only client_id + whitelisted events go out (no IP/UA).
  if (measurementId && apiSecret) {
    const url = "https://www.google-analytics.com/mp/collect" +
      `?measurement_id=${measurementId}&api_secret=${apiSecret}`;
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ client_id, events: stamped }),
    }).catch(() => {});
  }

  return new Response(null, { status: 204 });
}
// Non-POST methods get an automatic 405 from Pages (only onRequestPost is defined),
// same as functions/api/like.js.
