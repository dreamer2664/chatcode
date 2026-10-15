# The slate — yt-training-s1

Ten slots, ten distinct subjects. Machine-readable source of truth:
[`slate-registry.json`](slate-registry.json); rules in [`README.md`](README.md).
Consistency is enforced by `python3 tests/editorial_check.py`.

| Slot | Format | Title | Owner | Status |
|---|---|---|---|---|
| YT01 | evidence-led explainer | How Git Actually Remembers Everything | odysseus | reserved (PR #70) |
| YT02 | real screen tutorial | Verify Anything: SHA-256 in the Real World | — | pitched, unclaimed |
| YT03 | mini-documentary | The Day of Two Noons: How Railroads Invented Your Time Zone | — | pitched, unclaimed |
| YT04 | data story | The 5,000-Call Day | odysseus | reserved (PR #71) |
| YT05 | how a system works | How Video Compression Squeezes Reality | odysseus | reserved (PR #72) |
| YT06 | misconception investigation | The 10% Brain Myth: Anatomy of a Bad Idea | — | pitched, unclaimed |
| YT07 | practical build walkthrough | Build a URL Shortener From Scratch (and Break It) | — | pitched, unclaimed |
| YT08 | object biography | Ten Lines That Swallowed Retail: The Barcode | — | pitched, unclaimed |
| YT09 | visual thought experiment | Check Into Hilbert's Hotel | — | pitched, unclaimed |
| YT10 | original-format capstone | The Great Sorting Race | — | pitched, unclaimed |

## Collision record (checked 2026-10-15)

- **YT01 vs YT02** — both touch hashes. Differentiated: YT01 explains git's
  storage design; YT02 is a hands-on verification skill for non-programmers.
- **YT03 vs YT06** — both are "how an idea travels" stories. Differentiated:
  YT03 is a policy event with actors and dates; YT06 is the lineage of a false
  claim with a named rejection.
- **YT05 vs YT10** — both measure algorithmic work. Differentiated: YT05
  explains one codec's mechanisms; YT10 races eight algorithms in one bespoke
  instrument and reports measured counters.
- All other pairs: distinct premises per the registry's `premise_key`s; the
  checker's token-overlap pass reports no unexplained collisions.

## Rejected premises

| premise | slot | why rejected |
|---|---|---|
| Einstein endorsed the 10% claim | YT06 | Einstein Archives (Caltech) 2004 search found no evidence; kept as the film's apocrypha example, never as fact |

## Source-verification status

All ten slots carry a `sources_verified` record dated 2026-10-15. Open items
inside dossiers (marked "open item") must be closed before final export — the
delivery validator rejects manifests whose evidence does not match, and the
editorial review will check that quoted passages are primary-sourced.
