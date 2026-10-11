# PHRASES — the parser's test table (V2, t-20261011-f697)

Anchor for every relative date: **2026-10-11 (Sunday), 09:00 local**.
`tests/test_parser.js` parses this table and asserts every row passes.
Expected parses are written as JSON: `[{"text","due","priority"}]`.

| utterance | expected parse |
|---|---|
| buy milk and call mom tomorrow at five | `[{"text":"buy milk","due":null,"priority":"normal"},{"text":"call mom","due":"2026-10-12T17:00","priority":"normal"}]` |
| um please buy milk | `[{"text":"buy milk","due":null,"priority":"normal"}]` |
| call the dentist asap | `[{"text":"call the dentist","due":null,"priority":"high"}]` |
| water the plants sometime next week | `[{"text":"water the plants","due":"2026-10-18","priority":"low"}]` |
| pay rent on friday | `[{"text":"pay rent","due":"2026-10-16","priority":"normal"}]` |
| remind me to email Sam today | `[{"text":"email Sam","due":"2026-10-11","priority":"normal"}]` |
| take out the trash tonight | `[{"text":"take out the trash","due":"2026-10-11T18:00","priority":"normal"}]` |
| buy eggs, bread and butter | `[{"text":"buy eggs","due":null,"priority":"normal"},{"text":"buy bread","due":null,"priority":"normal"},{"text":"buy butter","due":null,"priority":"normal"}]` |
| schedule the demo at 9:30 am tomorrow | `[{"text":"schedule the demo","due":"2026-10-12T09:30","priority":"normal"}]` |
| no rush on updating the readme | `[{"text":"updating the readme","due":null,"priority":"low"}]` |
| pick up the kids at four | `[{"text":"pick up the kids","due":"2026-10-11T16:00","priority":"normal"}]` |
| send the contract to legal by monday urgent | `[{"text":"send the contract to legal","due":"2026-10-12","priority":"high"}]` |
| book a table for two on saturday | `[{"text":"book a table for two","due":"2026-10-17","priority":"normal"}]` |
| uh, call Anna back in two hours | `[{"text":"call Anna back","due":"2026-10-11T11:00","priority":"normal"}]` |
| flip the switch and check the logs | `[{"text":"flip the switch","due":null,"priority":"normal"},{"text":"check the logs","due":null,"priority":"normal"}]` |

Notes (what the table pins): conjunction and comma splitting with verb
carry-over; filler and courtesy stripping; natural dates (today / tonight /
tomorrow / on+by+next weekday / next week / in N hours-days); clock times
including bare afternoon numbers ("at four" = 16:00) and "for two" NOT being
a time; priorities high/low with the markers removed from the text.
