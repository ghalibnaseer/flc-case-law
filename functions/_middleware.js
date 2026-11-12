/**
 * Shared-password gate for the FLC case law database (Cloudflare Pages Functions).
 *
 * Runs on Cloudflare's server before any file is sent, including data/cases.json,
 * so nothing in the database can be read without the username and password.
 *
 * Set two encrypted environment variables in the Cloudflare Pages project
 * (Settings > Variables and Secrets), for Production and Preview:
 *   DB_USER      the shared username
 *   DB_PASSWORD  the shared password
 * If either is missing, every request is refused (the gate fails closed).
 */
const REALM = "FLC case law database";

function safeEqual(a, b) {
  // Compare in constant time so the password cannot be guessed from response times.
  const enc = new TextEncoder();
  const x = enc.encode(a), y = enc.encode(b);
  let diff = x.length ^ y.length;
  for (let i = 0; i < Math.max(x.length, y.length); i++) diff |= (x[i] || 0) ^ (y[i] || 0);
  return diff === 0;
}

function refuse() {
  return new Response("Members only. Please sign in with the username and password provided by the firm.", {
    status: 401,
    headers: {
      "WWW-Authenticate": `Basic realm="${REALM}", charset="UTF-8"`,
      "Cache-Control": "no-store",
      "X-Robots-Tag": "noindex, nofollow",
      "Content-Type": "text/plain; charset=utf-8",
    },
  });
}

export async function onRequest({ request, env, next }) {
  const user = env.DB_USER, pass = env.DB_PASSWORD;
  if (!user || !pass) return refuse();

  const header = request.headers.get("Authorization") || "";
  const [scheme, encoded] = header.split(" ");
  if (scheme !== "Basic" || !encoded) return refuse();

  let given;
  try {
    given = new TextDecoder().decode(Uint8Array.from(atob(encoded), c => c.charCodeAt(0)));
  } catch {
    return refuse();
  }
  const i = given.indexOf(":");
  if (i < 0) return refuse();
  const okUser = safeEqual(given.slice(0, i), user);
  const okPass = safeEqual(given.slice(i + 1), pass);
  if (!(okUser && okPass)) return refuse();

  const res = await next();
  const out = new Response(res.body, res);
  out.headers.set("Cache-Control", "private, no-store");
  out.headers.set("X-Robots-Tag", "noindex, nofollow");
  out.headers.set("X-Frame-Options", "DENY");
  out.headers.set("Referrer-Policy", "no-referrer");
  return out;
}
