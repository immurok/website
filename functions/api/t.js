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
// Env (Pages project settings -> Environment variables / Secrets):
//   GA_MEASUREMENT_ID  e.g. "G-XXXXXXXXXX"
//   GA_API_SECRET      GA4 Measurement Protocol API secret

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

  // Forward to GA4 Measurement Protocol. Fire-and-forget: GA failures must not
  // surface to the client. Only client_id + whitelisted events go out (no IP/UA).
  if (env.GA_MEASUREMENT_ID && env.GA_API_SECRET) {
    const url = "https://www.google-analytics.com/mp/collect" +
      `?measurement_id=${env.GA_MEASUREMENT_ID}&api_secret=${env.GA_API_SECRET}`;
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ client_id, events }),
    }).catch(() => {});
  }

  return new Response(null, { status: 204 });
}
// Non-POST methods get an automatic 405 from Pages (only onRequestPost is defined),
// same as functions/api/like.js.
