/**
 * quality/spring.mjs (Leonidas, M2 t-20261013-0bd4)
 * Real spring physics for scenes: a damped harmonic oscillator integrated
 * with semi-implicit Euler at a FIXED 1/240s substep, so a value is a
 * deterministic function of (params, time) — every frame re-simulates from
 * t=0, no hidden state, no linear tweens anywhere in this lane.
 *
 *   m·x'' = -k·(x - target) - c·x'
 *
 * Underdamped springs (dampingRatio < 1) overshoot the target before
 * settling; that overshoot is the visible difference from an ease curve
 * and is asserted in tests/quality.test.mjs.
 */

export const SUBSTEP = 1 / 240;

function check({ from, to, stiffness, damping, mass }) {
  for (const [k, v] of Object.entries({ from, to, stiffness, damping, mass })) {
    if (!Number.isFinite(v)) throw new Error(`spring: ${k} must be finite`);
  }
  if (stiffness <= 0 || mass <= 0 || damping < 0) {
    throw new Error('spring: stiffness/mass must be > 0, damping >= 0');
  }
}

/** Damping ratio ζ = c / (2·√(k·m)). ζ<1 overshoots, ζ=1 is critical. */
export function dampingRatio({ stiffness, damping, mass }) {
  return damping / (2 * Math.sqrt(stiffness * mass));
}

/** Spring constant helper: pick k,c from a desired ζ and natural frequency ω (rad/s). */
export function springParams({ stiffness = 120, zeta = 0.55, mass = 1 } = {}) {
  if (!(zeta > 0)) throw new Error('springParams: zeta must be > 0');
  return { stiffness, mass, damping: 2 * zeta * Math.sqrt(stiffness * mass) };
}

/**
 * Value of the spring at `time` (seconds), simulated deterministically
 * from t=0 with the given initial velocity. Cost is O(time/SUBSTEP);
 * scenes call this per animated property per frame.
 */
export function springAt(params, time) {
  const p = { velocity: 0, ...params };
  check(p);
  if (!(time >= 0)) throw new Error('springAt: time must be >= 0');
  let x = p.from, v = p.velocity;
  const steps = Math.round(time / SUBSTEP);
  for (let i = 0; i < steps; i++) {
    const a = (-p.stiffness * (x - p.to) - p.damping * v) / p.mass;
    v += a * SUBSTEP;
    x += v * SUBSTEP;
  }
  return x;
}

/** Per-frame track: values[i] is the spring value at frame i (frame/fps). */
export function simulateSpring(params, { fps, duration }) {
  if (!Number.isInteger(fps) || fps <= 0 || !(duration > 0)) {
    throw new Error('simulateSpring: fps/duration invalid');
  }
  const n = Math.round(fps * duration);
  const out = new Array(n);
  for (let f = 0; f < n; f++) out[f] = springAt(params, f / fps);
  return out;
}

/** True if the track crosses past `to` (visible overshoot), false for tweens. */
export function overshoots(track, { from, to }) {
  if (from === to) return false;
  const dir = Math.sign(to - from);
  return track.some(v => (v - to) * dir > 1e-9);
}

/** First time (s) after which the spring stays within eps of target, or null. */
export function settleTime(params, { eps = 0.5, maxTime = 10 } = {}) {
  let last = 0;
  const steps = Math.round(maxTime / SUBSTEP);
  let x = params.from, v = params.velocity ?? 0;
  for (let i = 0; i <= steps; i++) {
    if (Math.abs(x - params.to) > eps) last = i * SUBSTEP;
    const a = (-params.stiffness * (x - params.to) - params.damping * v) / params.mass;
    v += a * SUBSTEP; x += v * SUBSTEP;
  }
  return last === 0 ? 0 : last + SUBSTEP;
}
