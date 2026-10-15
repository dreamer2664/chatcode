# Editorial lab (V01, t-20261015-484f)

The slate is the campaign's collision map: ten slots, ten distinct subjects,
each researched enough that a production owner can start work the same day.

| file | what it is |
|---|---|
| `slate-registry.json` | machine-readable registry — slots, owners, premise keys, source-verification records, rejected claims |
| `SLATE.md` | human-readable view and reservation rules |
| `pitches/YT02..YT10.md` | the seven unclaimed pitch dossiers (audience, promise, timed outline, ≥3 sources, claim ledger, rights) |
| `research-example-YT06.md` | the research standard, shown end to end — checked passages and one rejected claim |
| `../../tests/editorial_check.py` | the automated consistency/collision checker (7 tests in `test_editorial_check.py`) |

## Reserving a slot

1. Claim the production card for the slot (V05–V14), not this one.
2. Put your name in `slate-registry.json` (`owner` + `status: reserved`).
3. Run `python3 tests/editorial_check.py` — it must pass.
4. If your topic is closer to another slot than the checker can see, add a
   `differentiation` note rather than weakening the check.

## Replacing a pitch

Any worker may propose a stronger topic for an **unproduced** slot. The old
premise moves to `rejected[]` with a reason — the slate keeps its history,
append-only, like everything else in this campaign.

## What a usable dossier contains

- a specific viewer and a promise the film can actually keep in 300–330 s;
- a timecoded outline covering the whole film (≥20 purposeful shots for the
  production card to build against);
- ≥3 credible sources, at least one primary where one exists, each with what it
  is *for*;
- a claim ledger: every material factual claim → source → timestamp in the film;
- a rights/asset strategy where everything on screen is original or logged;
- honest open items. An unresolved question written down beats a confident
  sentence that cannot be sourced on export day.
