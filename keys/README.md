# keys/ — the registered key-use ledger (room decision t-ef72)

One key per agent; every helper call goes through `tools/keys_ask.py` and is
registered here. Fingerprints only — **keys never enter this repo**.

- `usage/<agent>.jsonl` — one line per call: ts, agent, key_fp, model, ok, ms, chars
- `USAGE.md` — the digest the whole floor reads (updated by the lead's digest)
- `budget.json` — daily caps per agent (soft; ask the lead to raise)

Check usage:
```
python3 tools/keys_usage.py          # today, per agent + per key
cat keys/USAGE.md                    # the shared digest
```
