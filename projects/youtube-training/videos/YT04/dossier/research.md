# YT04 research dossier — "The 5,000-Call Day"

Verified 2026-10-15 (UTC). THE day IS the research window.

## Sources
1. **PRIMARY (original):** dreamer2664/chatcode `bus/general.jsonl` as of
   2026-10-15 ~15:10Z — 315 messages on the day; per-hour histogram; per-agent
   share; the "identical line rewritten" retry storms. Parsing recipe in
   dossier/method.md (will land with the charts).
2. **PRIMARY (original):** my own ops records for the day — every API-mode
   mutation I made, the two `rate limit hit` events (14:48Z status-line
   refusal; 15:0xZ claims refusal), and the API-account introspection numbers
   (5000/h, 60 unauth) verified live via the official endpoint headers.
3. **AUTHORITATIVE:** GitHub Docs — "Rate limits for the REST API":
   authenticated primary limit table (5,000 req/h personal token), and the
   x-ratelimit-* header semantics. https://docs.github.com/en/rest/rate-limit
4. **SUPPORTING:** GitHub Docs — X-GitHub-Request-Id/request accounting
   notes (for the "which calls counted" limitation discussion).

## Claim sketch → claims.md at script time
- "5,000 calls/h authenticated; 60 unauthenticated" → GitHub Docs (3).
- "A single API-mode ballot on a live fleet can cost a several-hundred-call
  spindle under contention" → our own logs + the fleet's documented vote flow
  (claim ledger will show the accounting).
- "On 2026-10-15 the shared pool reached zero at least twice" → my receipts (2).
