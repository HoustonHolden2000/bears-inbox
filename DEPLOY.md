# bears-inbox — deploy path (Render)

**State 2026-07-28:** code + blueprint READY, self-test PASS, binds `0.0.0.0:$PORT` for Render.
**Blocker to a live URL:** no Render CLI / API token / credential exists on this machine
(verified: `.vanta_secrets` holds only the 5 model keys; no RENDER_* env). The Render
account exists (history: `github.com/HoustonHolden2000/vanguard-shield` + render.yaml),
but it is login-walled from here. A real HTTPS URL cannot be minted headless without one credential.

## Recommended unblock (lowest Brad-touch): drop a Render API key out-of-band
Same channel Brad already uses for the feed key. Once `RENDER_API_KEY` is in the
env / `.vanta_secrets`, Maestro deploys fully headless:
1. Create web service `bears-inbox` from this blueprint (Starter plan + 1GB persistent disk).
2. Set `IRONHALO_FEED_KEY` env (the shared secret) via API — never printed.
3. Read back the live `https://bears-inbox.onrender.com` URL, curl `/health` to prove it,
   and hand Brad the VERIFIED URL to relay to Atlas (Matt).

## Alternative (one Brad-touch): Render dashboard
Render > New > Blueprint > point at a repo containing this folder > it reads render.yaml >
enter `IRONHALO_FEED_KEY` when prompted > Render emits the URL. (Avoided by default — it's a Brad-touch.)

## Billing note (tiny, Brad-lane)
Persistent disk + always-on = Render **Starter ~$7/mo**. Free tier spins down (cold starts)
and has **ephemeral disk** (drops received packets on restart) — not acceptable for an inbox.
Recommend Starter.

## Naming
Service is **bears-inbox**, not vanguard-shield. Bears infra wears the Bears' name (Brad, 07-28).
