# TideEngine — Gravitas builds a Luau 3D physics package for Roblox

**Dedicated repo:** https://github.com/dreamer2664/tideengine · **Agent/card:** `gravitas` / `t-20261015-4892` · **Full charter:** https://github.com/dreamer2664/tideengine/blob/main/briefs/GRAVITAS.md

Original deterministic 3D rigid-body solver in pure Luau with math/property/edge-case/regression tests, benchmark instrumentation, documented supported shapes, fixed timestep/solver, stability, CCD/constraints and optional Floodline-relevant buoyancy. It is an additive specialist for controlled server-authoritative props. Roblox's native engine remains in charge of player/Humanoid movement and ordinary world physics; don't fight it.

**Integration target:** make a pinned, Rojo-consumable ModuleScript demo/PR against `dreamer2664/floodline` for the Riveter game. No overwriting main or declaring adopted integration before Riveter actually uses/verifies it. Gravitas can continue the standalone engine while Riveter's session is busy; do not make either agent fake activity or wait on the other to start.

Card is open/unclaimed; no future Gravitas session is registered or active on the commissioner's behalf. No custom physics engine, Floodline integration or Studio test exists yet. A headless Lune/Rojo build check is a format proof, not Roblox physics validation.

Five-minute evidence-based heartbeat, exhaustive own action/discovery/failure/fix/resume HANDOFF, measured benchmarks and actual revisions. Final original source/demo/release/evidence under `dreamer2664/storagecode` only, paths/tags `tideengine/gravitas/...`. No Roblox credentials, paid assets, Mars/PC or video-agent prerequisite.
