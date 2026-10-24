// Redirects /download/<target> to the latest GitHub release asset for that
// platform, so the download page never has to be edited when a new version
// ships.
//
// GET /download/mac        -> latest .pkg from immurok/app-macos
// GET /download/win-x64    -> latest *-x64-setup.exe from immurok/app-win
// GET /download/win-arm64  -> latest *-arm64-setup.exe from immurok/app-win
// GET /download/linux-deb-x64    -> latest *_amd64.deb from immurok/app-linux-rs
// GET /download/linux-deb-arm64  -> latest *_arm64.deb
// GET /download/linux-rpm-x64    -> latest *.x86_64.rpm
// GET /download/linux-rpm-arm64  -> latest *.aarch64.rpm
// GET /download/linux-arch-x64   -> latest *-x86_64.pkg.tar.zst (Arch / pacman)
// GET /download/linux-arch-arm64 -> latest *-aarch64.pkg.tar.zst
//
// Resolved URLs are cached at Cloudflare's edge (Cache API) under two keys:
//   * a fresh copy (CACHE_TTL) that normally answers requests, and
//   * a long-lived copy (STALE_TTL) used as a fallback when GitHub cannot be
//     reached or answers with an error.
//
// GITHUB_TOKEN (Pages secret) MUST be set in production. Without it the
// request is unauthenticated and GitHub rate-limits it per source IP
// (60 req/hour). Workers share Cloudflare's egress IPs with every other
// Worker on the platform, so that quota is almost always already exhausted
// by other tenants and the lookup fails with 403 regardless of our own
// traffic. A fine-grained token with no permissions is enough for public
// repos and raises the limit to 5000 req/hour, counted per token.
//
// When the lookup fails and no stale copy exists either, the user is sent to
// the repo's releases page instead of getting a 502, and that fallback is
// cached briefly so a cold edge node does not hammer GitHub on every request.

const TARGETS = {
  'mac': { repo: 'immurok/app-macos', match: /\.pkg$/i },
  'win-x64': { repo: 'immurok/app-win', match: /-x64-setup\.exe$/i },
  'win-arm64': { repo: 'immurok/app-win', match: /-arm64-setup\.exe$/i },
  'linux-deb-x64': { repo: 'immurok/app-linux-rs', match: /_amd64\.deb$/i },
  'linux-deb-arm64': { repo: 'immurok/app-linux-rs', match: /_arm64\.deb$/i },
  'linux-rpm-x64': { repo: 'immurok/app-linux-rs', match: /\.x86_64\.rpm$/i },
  'linux-rpm-arm64': { repo: 'immurok/app-linux-rs', match: /\.aarch64\.rpm$/i },
  'linux-arch-x64': { repo: 'immurok/app-linux-rs', match: /-x86_64\.pkg\.tar\.zst$/i },
  'linux-arch-arm64': { repo: 'immurok/app-linux-rs', match: /-aarch64\.pkg\.tar\.zst$/i },
};

const CACHE_TTL = 600;             // seconds, normal re-resolve interval
const STALE_TTL = 7 * 24 * 3600;   // seconds, last-known-good fallback
const FAILURE_TTL = 60;            // seconds, back off after a failed lookup

function redirect(location, ttl) {
  return new Response(null, {
    status: 302,
    headers: {
      'Location': location,
      'Cache-Control': `public, max-age=${ttl}`,
    },
  });
}

async function resolveLatestAsset(target, env) {
  const headers = {
    'User-Agent': 'immurok-website',
    'Accept': 'application/vnd.github+json',
  };
  if (env.GITHUB_TOKEN) headers['Authorization'] = `Bearer ${env.GITHUB_TOKEN}`;

  const apiRes = await fetch(`https://api.github.com/repos/${target.repo}/releases/latest`, { headers });
  if (!apiRes.ok) {
    throw new Error(`GitHub API ${apiRes.status} ` +
      `(ratelimit remaining=${apiRes.headers.get('x-ratelimit-remaining')}, ` +
      `token=${env.GITHUB_TOKEN ? 'yes' : 'NO'})`);
  }
  const release = await apiRes.json();
  const asset = (release.assets || []).find((a) => target.match.test(a.name));
  if (!asset) throw new Error(`no asset matching ${target.match} in ${release.tag_name}`);
  return asset.browser_download_url;
}

export async function onRequestGet({ params, env }) {
  const target = TARGETS[params.target];
  if (!target) return new Response('not found', { status: 404 });

  const cache = caches.default;
  const freshKey = new Request(`https://immurok-download-cache.internal/${params.target}`);
  const staleKey = new Request(`https://immurok-download-cache.internal/stale/${params.target}`);

  const fresh = await cache.match(freshKey);
  if (fresh) return fresh;

  try {
    const url = await resolveLatestAsset(target, env);
    await cache.put(freshKey, redirect(url, CACHE_TTL));
    await cache.put(staleKey, redirect(url, STALE_TTL));
    return redirect(url, CACHE_TTL);
  } catch (err) {
    console.error(`download/${params.target}: ${err.message}`);
    const stale = await cache.match(staleKey);
    const fallback = stale
      ? redirect(stale.headers.get('Location'), FAILURE_TTL)
      : redirect(`https://github.com/${target.repo}/releases/latest`, FAILURE_TTL);
    await cache.put(freshKey, fallback.clone());
    return fallback;
  }
}
