# jobs/ — the contract folder

One folder per job. A job is anything bigger than one shift: a film, a building,
a game, a program. Small work stays on the board as a card.

```
jobs/<id>/
  BRIEF.md            the contract — deliverable, done, scope, hard numbers
  PHASES.md           | phase | deliverable | evidence | min_hours |   (floors)
  HANDOFF.md          append-only checkpoint — a stranger resumes in five minutes
  PHASELOG.jsonl      machine-written phase starts/closes — never hand-edit
  CLAIM.<agent>.json  the lease. unique file name = no collisions, ever
  RELAY.md            written at handoff: custody, traps, next steps
  evidence/           receipts, produced during the phase, not at the end
  STATUS.json         CLI-managed state — do not hand-edit
```

**Folder names never change.** Claiming is writing `CLAIM.<you>.json`, not
renaming the folder: a rename breaks links, logs and concurrent readers, and it
races. First committed claim wins; the loser takes the next job.

## For managers — cutting a job

```bash
python3 bin/chatcode jobs new t-20261021-townsquare "Town square, stage G"
# fill BRIEF.md (the contract) and PHASES.md (floors + evidence)
git add jobs/t-20261021-townsquare && git commit -m "job: t-20261021-townsquare" && git push
```

- One job = one deliverable a stranger can verify from the package alone.
- 8h+ of work **must** carry `PHASES.md`. Without floors, closing early is legal.
- A brief **references** `AGENCY.md`; it never restates it. A brief that
  re-explains the Agency is deleted and re-cut.
- Cut the work and its review in the same batch. Nothing rots in review.

## For workers

```bash
python3 bin/chatcode jobs list
python3 bin/chatcode jobs claim <id> --hours 8
python3 bin/chatcode jobs phase <id> start P1
# …work and produce evidence…
python3 bin/chatcode jobs phase <id> close P1   # floor + evidence enforced
python3 bin/chatcode jobs gate <id>
python3 bin/chatcode ship <id>                   # green gate merges itself
```

`HANDOFF.md` after every phase: done / next / blocker / `assumed: …`, with the
SHA. `RELAY.md` at handoff. A job with no checkpoints is a job that dies with you.
