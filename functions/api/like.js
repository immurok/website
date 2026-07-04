// Like counter for blog posts, backed by Workers KV (binding: LIKES).
//
// GET  /api/like?slug=<slug>          -> { count }
// POST /api/like  body: {"slug":...}  -> { count, liked } | { count, alreadyLiked }
//
// Dedup: one like per IP per post (salted SHA-256 of IP, 30-day TTL).
// Rate limit: 10 POSTs per IP per minute.

const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,99}$/;
const DEDUP_TTL = 60 * 60 * 24 * 30;
const RATE_LIMIT = 10;

async function sha256Hex(s) {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s));
  return [...new Uint8Array(digest)].map(b => b.toString(16).padStart(2, '0')).join('');
}

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' },
  });
}

async function getCount(env, slug) {
  return parseInt(await env.LIKES.get(`count:${slug}`) || '0', 10);
}

export async function onRequestGet({ request, env }) {
  const slug = new URL(request.url).searchParams.get('slug') || '';
  if (!SLUG_RE.test(slug)) return json({ error: 'bad slug' }, 400);
  return json({ count: await getCount(env, slug) });
}

export async function onRequestPost({ request, env }) {
  let slug = '';
  try { slug = (await request.json()).slug || ''; } catch {}
  if (!SLUG_RE.test(slug)) return json({ error: 'bad slug' }, 400);

  const ip = request.headers.get('CF-Connecting-IP') || '0.0.0.0';
  const salt = env.LIKE_SALT || 'immurok-like-v1';

  const minute = Math.floor(Date.now() / 60000);
  const rlKey = `rl:${await sha256Hex(salt + ip)}:${minute}`;
  const hits = parseInt(await env.LIKES.get(rlKey) || '0', 10);
  if (hits >= RATE_LIMIT) return json({ error: 'rate limited' }, 429);
  await env.LIKES.put(rlKey, String(hits + 1), { expirationTtl: 120 });

  const dedupKey = `ip:${await sha256Hex(salt + ip + slug)}`;
  if (await env.LIKES.get(dedupKey)) {
    return json({ count: await getCount(env, slug), alreadyLiked: true });
  }
  await env.LIKES.put(dedupKey, '1', { expirationTtl: DEDUP_TTL });

  const count = await getCount(env, slug) + 1;
  await env.LIKES.put(`count:${slug}`, String(count));
  return json({ count, liked: true });
}
