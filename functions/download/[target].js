// Redirects /download/<target> to the latest GitHub release asset for that
// platform, so the download page never has to be edited when a new version
// ships.
//
// GET /download/mac        -> latest .pkg from immurok/app-macos
// GET /download/win-x64    -> latest *-x64-setup.exe from immurok/app-win
// GET /download/win-arm64  -> latest *-arm64-setup.exe from immurok/app-win
//
// Resolved URLs are cached at Cloudflare's edge (Cache API) for 10 minutes so
// normal traffic makes at most a handful of GitHub API calls per hour,
// staying well under the unauthenticated 60 req/hour rate limit. Set
// GITHUB_TOKEN (Pages env var) to raise that ceiling if traffic grows.

const TARGETS = {
  'mac': { repo: 'immurok/app-macos', match: /\.pkg$/i },
  'win-x64': { repo: 'immurok/app-win', match: /-x64-setup\.exe$/i },
  'win-arm64': { repo: 'immurok/app-win', match: /-arm64-setup\.exe$/i },
};

const CACHE_TTL = 600; // seconds

export async function onRequestGet({ params, env }) {
  const target = TARGETS[params.target];
  if (!target) return new Response('not found', { status: 404 });

  const cacheKey = new Request(`https://immurok-download-cache.internal/${params.target}`);
  const cache = caches.default;
  const cached = await cache.match(cacheKey);
  if (cached) return cached;

  const headers = {
    'User-Agent': 'immurok-website',
    'Accept': 'application/vnd.github+json',
  };
  if (env.GITHUB_TOKEN) headers['Authorization'] = `Bearer ${env.GITHUB_TOKEN}`;

  const apiRes = await fetch(`https://api.github.com/repos/${target.repo}/releases/latest`, { headers });
  if (!apiRes.ok) {
    return new Response('failed to resolve latest release', { status: 502 });
  }
  const release = await apiRes.json();
  const asset = (release.assets || []).find((a) => target.match.test(a.name));
  if (!asset) {
    return new Response('no matching asset in latest release', { status: 502 });
  }

  const response = new Response(null, {
    status: 302,
    headers: {
      'Location': asset.browser_download_url,
      'Cache-Control': `public, max-age=${CACHE_TTL}`,
    },
  });
  await cache.put(cacheKey, response.clone());
  return response;
}
