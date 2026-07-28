# Iron Halo → Bears Calibration Inbox (receiver-only)

Built by Maestro (Seat A) 2026-07-28 from Matthew Lambert's RECEIVER SETUP spec.
**Status: CODE COMPLETE + localhost self-test PASS. NOT deployed. NOT keyed. No reply sent to Atlas.**

## What it is
One-way receiver. Iron Halo PUSHes calibration/drill packets; the Bears only read.
- `ironhalo_receiver.py serve` — HTTPS inbox: `POST /inbox`, `Authorization: Bearer <key>`, 401 on bad/missing key, appends to hash-chained `ironhalo_inbox.jsonl`, returns `200 {"ok":true}`. `GET /health` returns count only (never packet data).
- `read_inbox.py` — the Bears' READ-ONLY view + chain verify.
- `ironhalo_receiver.py selftest` — localhost proof (good→200, bad/missing→401, only-good-stored). **Verified PASS 2026-07-28.**

## Fail-closed properties (built into plumbing, not policy)
- Key read from env `IRONHALO_FEED_KEY` ONLY. Never written to disk, logged, or printed. Server refuses to start if unset.
- Default bind 127.0.0.1. Going public is a deploy decision, not a code default.
- Auth header never logged. Store is append-only + SHA-256 chained.
- No outbound route to Iron Halo exists anywhere in this module.

## THREE GATES BEFORE THIS GOES LIVE (all Brad's gavel)
1. **HOST** — where the public URL lives. Options:
   - Bears' existing **Render** account (persistent disk, simplest for an append store) — clean separation from Vanguard's Netlify/GuardOps.
   - A serverless function (Netlify/Cloudflare) that forwards to the Lenovo store.
   - Decision needs: account, custom domain, TLS. **Brad picks.**
2. **REAL KEY** — Matt's message carried `PASTE_KEY_HERE` (placeholder; no real key was exposed). When the real key arrives it goes STRAIGHT into the host's env / a local `.env` — **never pasted into a chat/prompt/output.** (A CLICK_HERE .cmd can set it without Brad typing it into the model.)
3. **REPLY TO "ATLAS"** — the spec says reply to Atlas with the inbox URL. That is a send to an external channel = Brad-lane. Also: "Atlas" is not a route the Bears currently hold — **who/what is Atlas, and does Brad relay or do the Bears get a channel?**

## Data boundary (Matt's guardrail, upheld)
Test/drill only (`calibration:true` / `drill:true`). Real plates/faces/officer names/client sites do NOT cross until Brad + Matt agree **in writing**. Default redacted.
