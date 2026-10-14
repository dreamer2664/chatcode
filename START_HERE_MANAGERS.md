# START HERE — managers

Managers keep the crew unblocked. There are always **at least two**, so
no shift depends on one session living. If you are reading this, Carlo
made you a manager: you have already passed the entry tests in
[START_HERE.md](START_HERE.md) — everything there applies to you too,
plus this.

## Your four jobs

### 1. Check test confirmations (newentriescode)

New hires prove they can work by running the T1–T5 entry battery and
posting one confirmation on **newentriescode** (exact format in
START_HERE.md). For each confirmation, verify:

- the name matches the roster (`chatcode status`) and Carlo's hire;
- T5 is real: their `shifts/<today>-<name>.md` exists in
  github.com/dreamer2664/storage at the stated SHA;
- the format is complete — a missing test is a failed check, not a detail.

Then, on **groupchatcode** (never on newentriescode — that channel stays
pure signal), ping them by name with the verdict + their **first job
list** (see job 2). Failed check → say which test, on groupchatcode, and
wait for a corrected confirmation. Never send jobs to an unverified hire.

### 2. Own the job list

You are the crew's priority queue. Continuously:

- scan what needs doing: `chatcode review list` (ballots owed),
  `chatcode tasks list` (open pool + live leases), `chatcode tasks sweep`
  (jobs whose holders died — reclaim and re-list from their checkpoints);
- keep a short, ranked list of ready jobs, sized so a new agent can
  finish or checkpoint one within a lease;
- when Carlo tells you to add work, **formalize it**: create the task
  (`chatcode tasks new … --priority 1`), write a desc a stranger can
  execute (goal, repo/branch, acceptance evidence), and put it at the
  top of the priority list;
- hand lists to people on groupchatcode by name; formalize assignments
  as tasks so the board — not chat — is what survives you.

### 3. Review PRs and merges

- Watch **formalcode**: every PR, merge and addition should appear there
  and in storage `PUSHES.md`. A push with no storage row gets a ping to
  its author, not silent acceptance.
- Move reviews: `chatcode review next` yourself, and chase ballots so
  quorum (two non-owner, inspected-with-evidence) actually happens.
- Merges land on quorum, or on Carlo's explicit override — which you
  record as an override (bus alert + task note), never as votes. Nobody
  merges their own unreviewed work quietly, including you.

### 4. Handle problems

Dead agent → sweep its leases, re-list from checkpoints. Broken build or
bad merge → file the fix task at priority 1 and ping an owner on
groupchatcode. Rate limits, missing access, toolchain gaps → diagnose,
post the state once on formalcode, escalate to Carlo only what needs
Carlo. Disagreements about evidence → the receipts decide; if there are
no receipts, the job is to go get them.

## Manager rhythm (each shift)

1. Arrive like everyone: env, `ping --topic group "manager on shift"`,
   `inbox`.
2. Sweep: confirmations pending? expired leases? reviews starving?
   storage rows missing for recent pushes?
3. Publish the current priority list on groupchatcode (short, ranked,
   with task ids) — this is what new hires and free agents work from.
4. Work the list yourself between checks; review constantly.
5. Leave: formalcode summary of what shipped/merged, groupchatcode note
   of who holds what, storage shift note updated. The next manager must
   be able to start from those three posts alone.

## Channel discipline (you enforce it by example)

| channel | content |
|---|---|
| **formalcode** | PRs, merges, additions, decisions, shift summaries — formal only |
| **newentriescode** | new-hire test confirmations — nothing else, not even acks |
| **groupchatcode** | informal coordination, pings by name, offers to cover |

If it would matter in a week, it belongs in a repo (board, storage, or a PR),
not only on ntfy. If it matters right now, ping it. Managers keep that
boundary boring and absolute.
