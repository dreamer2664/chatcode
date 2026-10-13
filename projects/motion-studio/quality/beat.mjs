/**
 * quality/beat.mjs (Leonidas, M2 t-20261013-0bd4)
 * Beat grids and cut locking. A beatMap is { beats:[s...], cuts:[s...] }
 * (Achilles M1 config shape); by construction here every cut IS a beat,
 * so a scene that changes composition only at `cuts` is beat-locked
 * provably, not by eyeballing a timeline.
 */

const EPS = 1e-9;

export function makeBeatMap({ bpm, duration, cutEveryBeats = 4, offset = 0 } = {}) {
  if (!Number.isFinite(bpm) || bpm <= 0) throw new Error('beat: bpm must be > 0');
  if (!Number.isFinite(duration) || duration <= 0) throw new Error('beat: duration must be > 0');
  if (!Number.isInteger(cutEveryBeats) || cutEveryBeats < 1) {
    throw new Error('beat: cutEveryBeats must be an integer >= 1');
  }
  const spb = 60 / bpm; // seconds per beat
  const beats = [];
  for (let t = offset, i = 0; t <= duration + EPS; t = offset + ++i * spb) {
    beats.push(Math.min(t, duration));
  }
  if (beats.length === 0 || beats[0] > 0) beats.unshift(0);
  const cuts = beats.filter((_, i) => i % cutEveryBeats === 0);
  return { beats, cuts, bpm, secondsPerBeat: spb };
}

/** Index of the beat at or before `time` (-1 before the first beat). */
export function beatIndexAt(beatMap, time) {
  let idx = -1;
  for (let i = 0; i < beatMap.beats.length; i++) {
    if (beatMap.beats[i] <= time + EPS) idx = i; else break;
  }
  return idx;
}

/** Phase within the current beat, 0..1 (0 exactly on a beat). */
export function beatPhase(beatMap, time) {
  const i = beatIndexAt(beatMap, time);
  if (i < 0) return 0;
  const start = beatMap.beats[i];
  const next = beatMap.beats[i + 1] ?? start + (beatMap.secondsPerBeat ?? 60 / beatMap.bpm);
  return Math.min(1, Math.max(0, (time - start) / (next - start)));
}

export function isBeat(beatMap, time, tol = 1e-6) {
  return beatMap.beats.some(b => Math.abs(b - time) <= tol);
}

export function nearestBeat(beatMap, time) {
  let best = null;
  for (const b of beatMap.beats) {
    if (best === null || Math.abs(b - time) < Math.abs(best - time)) best = b;
  }
  return best;
}

/** The cut in force at `time`: scenes switch composition only when this changes. */
export function cutAt(beatMap, time) {
  let idx = 0;
  for (let i = 0; i < beatMap.cuts.length; i++) {
    if (beatMap.cuts[i] <= time + EPS) idx = i; else break;
  }
  return idx;
}

/** Assert a proposed cut list is beat-locked; returns list of violations. */
export function validateCuts(beatMap, cuts, tol = 1e-6) {
  return cuts.filter(c => !isBeat(beatMap, c, tol))
    .map(c => `cut at ${c}s is not on a beat`);
}
