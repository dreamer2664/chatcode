# Neuralbrain — two collaborating agents, one persistent local coding brain

**Dedicated source:** https://github.com/dreamer2664/neuralbrain · **Requested collaboration channel:** https://ntfy.sh/neuralbrain

| Agent | Reserved first-wake card | Clean public charter | Own lane |
|---|---|---|---|
| **neuroforge** | `t-20261015-7d93` | [NEUROFORGE.md](https://github.com/dreamer2664/neuralbrain/blob/main/briefs/NEUROFORGE.md) | Small local code model, real adapter training/correction learning, ≤1GiB deployed inference, persistent queue worker. |
| **benchmate** | `t-20261015-afd1` | [BENCHMATE.md](https://github.com/dreamer2664/neuralbrain/blob/main/briefs/BENCHMATE.md) | Independent project/build/sandbox/holdout evaluation, adversarial tests and verified correction feedback. |

Two separate sessions, own isolated logs/status/folders, one shared repository. Collaborate on actual interfaces, tests, corrective examples and commit-level reproduction. Pair completion requires a running local model, hard cgroup whole-process-tree RAM cap, real continual job-queue worker and parameter/adaptor update which improves independent unseen sibling tests—not just a chatbot prompt or retrieval diary.

The worker keeps running without further chat prompts **while its actual OS process and queue worker are alive**. When empty it sleeps cheaply and admits it is idle; explicit stop/OS/safety/resource stop ends the process. This is not a promise that an AI privately reasons when idle or that producer sessions continue after ending.

The ntfy topic name is public and guessable; anyone can read/publish. Use only short safe commit/test/hash pointers, never code, commands, credentials or private data. Verify notifications against Git. The repo is the source of truth; format `NB1`. See each full charter.

**Commissioning truth:** both cards are open/unclaimed; no future agent was registered/awakened/claimed by the commissioner. No model, training correction, project-build benchmark, RAM measurement or agent activity yet. Five-minute truthful status and exhaustive own HANDOFF are required. Setup tests are not a model result.

Large weights/adapter and final reproducible artifact → `dreamer2664/storagecode` under `data/neuralbrain/<agent>/...`, immutable `neuralbrain/<agent>/...` Release tags. No weights in source Git. Mars stays paused; no cloud or paid API.
