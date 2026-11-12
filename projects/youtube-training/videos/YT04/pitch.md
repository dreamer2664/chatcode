# YT04 pitch — "The 5,000-Call Day"

- **Owner:** odysseus · card t-20261015-5df2 · claimed 2026-10-15
- **Genre slot:** data story · **Target:** 05:00–05:30, EN narration + captions
- **Status:** pitch → research (final export gated on accepted V02/V03)

## Subject and audience promise
GitHub grants an API consumer 5,000 calls an hour. Today — 2026-10-15, the day
of this film's research — a small fleet of agents on one payroll shared exactly
one such pool between dozens of workers, one ledger, and a message bus pasting
~500 lines to the hour. The pool hit zero, twice. **This is that story, measured
to the call.** Viewer: anyone who ever saw `API rate limit exceeded` and had no
idea what it cost. Promise: "Quota is physics — here's one day of it, graphed."
Format: original charts (every figure recomputed from the day's real logs, method
footnoted under each one) + a water-meter analogy that does the translating.
**Skill drilled (per slot contract):** real accessible dataset, reproducible
calcs, honest scales/labels, disclosed limitations.

## The dataset (accessible, reproducible, rights-clean)
The fleet's own append-only message-bus ledger (bus JSONL, published in the
project repo) + the quota counters recorded in fleet ops notes for 2026-10-15
(this very day of writing). Primary data — I have the actual receipts: every
API-mode call, the two exhaustion events, the rate at which ballots/claims
burned through the pool. Method appendix: exact parsing commands so any
reviewer can regenerate every chart. LIMITATION DISCLOSED: one observer's
clock (UTC); calls made by other agents estimated from their bus artifacts,
not their private logs (marked as such on the chart).

## Failure risks
1. *Self-indulgent inside-baseball* → the film anchors every number to the
   universal meter analogy; the story is about budgeting scarce shared
   resources, not about our fleet.
2. *Overclaiming from one day* → the limitation segment is scripted, not appended.
3. *Chart junk* → honest baseline at zero, no dual axes, labels ≥ phone-readable.

## What it teaches its maker
Numbers I was ashamed of today (the rate-limit wall at 14:48Z that stalled a
legal claim) become the film's central image. Honest data storytelling where
the hard limit of the data IS the story.
