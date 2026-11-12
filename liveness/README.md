# liveness/ — one pulse per agent

`chatcode pulse` writes `liveness/<agent>.json` (one file per agent, so there are
no write conflicts). `chatcode tower` renders the crew from these files; CI
regenerates `TOWER.md` every ten minutes.

Never hand-edit a pulse. A pulse older than 45 minutes means the agent is dead:
its leases are swept and its jobs return to the pool with their HANDOFF intact.

```bash
python3 bin/chatcode pulse --status WORKING --note "stage B, chunk 4/9"
python3 bin/chatcode tower
```
