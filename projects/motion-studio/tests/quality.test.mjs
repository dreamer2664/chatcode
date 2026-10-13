/**
 * tests/quality.test.mjs (Leonidas, M2 t-20261013-0bd4)
 * Springs overshoot and settle deterministically; cuts sit on beats;
 * the critic pays for real structure and starves a blank frame;
 * the lint bans the slop patterns; the demo scene paints via springs.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdtemp } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { PNG } from 'pngjs';

import { springAt, simulateSpring, springParams, overshoots, settleTime, dampingRatio } from '../quality/spring.mjs';
import { makeBeatMap, cutAt, beatPhase, validateCuts, isBeat } from '../quality/beat.mjs';
import { lintSceneSource, assertSceneClean } from '../quality/lint.mjs';
import { analyze } from '../quality/critic.mjs';
import { render } from '../scenes/spring-demo.mjs';

const spring = springParams({ stiffness: 90, zeta: 0.42 });

test('spring overshoots its target, then settles (not a tween)', () => {
  const track = simulateSpring({ ...spring, from: 0, to: 100 }, { fps: 24, duration: 3 });
  assert.equal(overshoots(track, { from: 0, to: 100 }), true);
  assert.ok(Math.abs(track.at(-1) - 100) < 1.5, `settled at ${track.at(-1)}`);
  assert.ok(dampingRatio(spring) < 1);
  assert.ok(settleTime({ ...spring, from: 0, to: 100 }) < 3);
});

test('spring is deterministic and not a straight line', () => {
  const a = springAt({ ...spring, from: -90, to: 0 }, 0.5);
  assert.equal(a, springAt({ ...spring, from: -90, to: 0 }, 0.5));
  const vals = [0.1, 0.2, 0.3, 0.4].map(t => springAt({ ...spring, from: 0, to: 100 }, t));
  const diffs = vals.slice(1).map((v, i) => v - vals[i]);
  assert.notEqual(diffs[0].toFixed(6), diffs[1].toFixed(6)); // velocity changes: acceleration is real
});

test('cuts are locked to beats by construction', () => {
  const bm = makeBeatMap({ bpm: 120, duration: 4, cutEveryBeats: 2 });
  assert.deepEqual(bm.cuts, [0, 1, 2, 3, 4].filter(v => v <= 4));
  assert.deepEqual(validateCuts(bm, bm.cuts), []);
  assert.ok(bm.cuts.every(c => isBeat(bm, c)));
  assert.equal(cutAt(bm, 1.2), 1);
  assert.ok(beatPhase(bm, 1.25) > 0.4 && beatPhase(bm, 1.25) < 0.6);
  assert.match(validateCuts(bm, [1.37])[0], /not on a beat/);
});

function pngFile(dir, name, paint) {
  const png = new PNG({ width: 96, height: 96 });
  for (let y = 0; y < 96; y++) for (let x = 0; x < 96; x++) {
    const i = (y * 96 + x) * 4;
    const [r, g, b] = paint(x, y);
    png.data[i] = r; png.data[i + 1] = g; png.data[i + 2] = b; png.data[i + 3] = 255;
  }
  const file = path.join(dir, name);
  return writeFile(file, PNG.sync.write(png)).then(() => file);
}

test('critic pays structured colour and starves a blank frame', async () => {
  const dir = await mkdtemp(path.join(tmpdir(), 'mstudio-critic-'));
  const rich = await pngFile(dir, 'rich.png', (x, y) =>
    (x + y) % 24 < 12 ? [224, 120, 64] : [x % 3 ? 127 : 40, 176 - y, 105]);
  const blank = await pngFile(dir, 'blank.png', () => [24, 24, 24]);
  const good = await analyze({ imagePath: rich, frame: 1, time: 0.04, beatMap: null, metrics: { contrast: 60, meanFrameDelta: 5 }, revision: 0 });
  const bad = await analyze({ imagePath: blank, frame: 1, time: 0.04, beatMap: null, metrics: { contrast: 0, meanFrameDelta: 0 }, revision: 0 });
  assert.ok(good.score > bad.score, `${good.score} vs ${bad.score}`);
  assert.ok(bad.score < 8 && bad.issues.length >= 2);
  assert.ok(bad.patch.emphasis > 0); // a fail comes with a repair the scene can apply
  const later = await analyze({ imagePath: blank, frame: 2, time: 0.08, beatMap: null, metrics: { contrast: 0, meanFrameDelta: 0 }, revision: 1 });
  assert.ok(later.patch.emphasis > bad.patch.emphasis); // bounded attempts still change the frame
});

test('lint bans slop and passes the demo scene', async () => {
  const dirty = `export function render(ctx){ ctx.fillStyle = ctx.createLinearGradient(0,0,9,9); const e = easing('linear'); }`;
  const rules = lintSceneSource(dirty).map(i => i.rule);
  assert.ok(rules.includes('no-gradient-fill') && rules.includes('no-linear-easing'));
  const demo = await readFile(new URL('../scenes/spring-demo.mjs', import.meta.url), 'utf8');
  assert.equal(assertSceneClean(demo, { filename: 'spring-demo.mjs' }), true);
});

test('demo scene paints deterministically and responds to a critic patch', () => {
  const calls = () => {
    const log = [];
    const ctx = new Proxy({ canvas: {} }, {
      get: (o, k) => k in o ? o[k] : (...a) => { log.push([k, ...a]); },
      set: (o, k, v) => { o[k] = v; log.push(['set', k, String(v)]); return true; },
    });
    render(ctx, { width: 960, height: 540, time: 0.65, duration: 4, fps: 24, frame: 16, beatMap: null, patch: null });
    return JSON.stringify(log);
  };
  assert.equal(calls(), calls());
  const plain = calls();
  const boostedLog = [];
  const ctx2 = new Proxy({ canvas: {} }, {
    get: (o, k) => k in o ? o[k] : (...a) => { boostedLog.push([k, ...a]); },
    set: (o, k, v) => { o[k] = v; return true; },
  });
  render(ctx2, { width: 960, height: 540, time: 0.65, duration: 4, fps: 24, frame: 16, beatMap: null, patch: { emphasis: 1 } });
  assert.notEqual(JSON.stringify(boostedLog), plain); // patch visibly changes the re-render
});
