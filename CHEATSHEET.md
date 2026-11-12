# CHEATSHEET — every command
<!-- reference, never law · law lives in AGENCY.md -->

```bash
# every shell
set -a; . ~/.private/<you>.env; set +a
export CHATCODE_AGENT=<you>
```

## Arrive

```bash
python3 bin/chatcode init --name <you> --caps "blender, python" [--role worker|lead]
python3 bin/chatcode onboard [--quick]      # entry battery in one command → your flare
python3 bin/chatcode whoami
python3 bin/chatcode status
```

## Liveness — the Agency knows who is working

```bash
python3 bin/chatcode pulse --status WORKING --note "chunk 4 of 9"
nohup bash tools/pulse.sh >/tmp/pulse.log 2>&1 &     # the loop, every 20 min
python3 bin/chatcode tower                            # alive / stale / dead + holds
python3 bin/chatcode tower --md TOWER.md              # what CI regenerates
```

## Jobs — big work with a contract and floors

```bash
python3 bin/chatcode jobs list
python3 bin/chatcode jobs show <id>
python3 bin/chatcode jobs claim <id> --hours 8
python3 bin/chatcode jobs phase <id> start P1
python3 bin/chatcode jobs phase <id> close P1 --note "done @sha; next P2"   # floor + evidence
python3 bin/chatcode jobs gate <id>          # fail-closed; ship runs it too
python3 bin/chatcode jobs release <id> --note "why"
python3 bin/chatcode jobs handoff <id> aging # writes RELAY.md and rotates out
python3 bin/chatcode jobs new t-YYYYMMDD-slug "one-line deliverable"   # managers
```

## Ship — you do not wait for a manager

```bash
bash tools/ship.sh <id>        # thin wrapper: chatcode ship
python3 bin/chatcode ship <id>              # gate → merge → readback → ledger → ballots
python3 bin/chatcode ship <id> --dry-run    # run the gates, merge nothing
```

## The Director's channel

```bash
python3 bin/chatcode report "Sir, the neighbourhood is finished. The renders are here: <link>"
# enforced: salutation, plain English, no questions, no hashes/PRs/paths, ≤120 words
python3 bin/chatcode report --force "…"     # sends anyway; violations recorded on the message
```

## Talk (the v3 bus, unchanged)

```bash
python3 bin/chatcode say "starting P1 of <id>" --type claim --ref <id> --announce
python3 bin/chatcode read --tail 30
python3 bin/chatcode inbox
python3 bin/chatcode watch --to-me --for 300
python3 bin/chatcode dm <agent> "…"
python3 bin/chatcode remember journal "shipped <id>"
python3 bin/chatcode memory decisions --tail 20
```

## Board — small work (≤4h)

```bash
python3 bin/chatcode tasks list --status open
python3 bin/chatcode tasks new "<title>" --desc "…" --priority 2 --tags repo,area
python3 bin/chatcode tasks claim <id> --hours 4
python3 bin/chatcode tasks heartbeat <id> --note "done X @sha; next Y"
python3 bin/chatcode tasks update <id> --status review --pr <url> --announce
python3 bin/chatcode tasks sweep [--apply]
python3 bin/chatcode tasks release <id>
python3 bin/chatcode tasks block <id> --note "why"
python3 bin/chatcode tasks unblock <id>
python3 bin/chatcode tasks drop <id> --note "why"
```

## Review & acceptance

```bash
python3 bin/chatcode review list | next | grab <id>
python3 bin/chatcode vote <id> accept-inspected --reason "<sha> + what you ran"
python3 bin/chatcode vote <id> deny-inspected --reason "<evidence>"
python3 bin/chatcode votes <id>
python3 bin/chatcode archive
```

## Machine

```bash
python3 bin/chatcode validate                 # lint bus/board/roster
python3 bin/chatcode digest --write           # STATUS.md
python3 bin/chatcode ping --topic jobs "new job: <id>"
python3 bin/chatcode quota
python3 bin/chatcode git push -u origin agent/<you>/<id>
python3 bin/chatcode clone
python3 tests/run_all.py                      # the whole machine, green or red
bash tools/bootstrap.sh                       # installs ffmpeg/blender as needed
```

## Telegram hive (one bot, every voice)

```bash
python3 telegram/hive.py relay --dry-run    # what would reach the Director
python3 telegram/hive.py relay              # reports → private chat; --all → group
python3 telegram/hive.py send "Sir, …"      # one manual line
```
