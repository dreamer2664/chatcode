// longform.test.mjs — dedicated tests for the V02 long-form orchestrator.
// Convention: node:test + node:assert/strict; real browser + real ffmpeg
// (same as integration.test.mjs). Nothing here fakes a render.
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, readFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { validateFilmSpec, shotCacheKey, checkSegmentsAgainstExceptions, buildFilm, probe, ENGINE_VERSION } from '../engine/longform.mjs';

const cfg = (duration) => ({ width: 320, height: 180, fps: 4, duration });
async function workspace(fn) {
  const dir = await mkdtemp(path.join(os.tmpdir(), 'longform-test-'));
  try { return await fn(dir); } finally { await rm(dir, { recursive: true, force: true }); }
}
const twoShotSpec = () => ({
  id: 'calib-mini',
  shots: [
    { id: 'a', scene: 'scenes/demo.mjs', config: cfg(2) },
    { id: 'b', scene: 'scenes/demo.mjs', config: { ...cfg(2), seed: 7 } },
  ],
});

test('validateFilmSpec refuses malformed specs', () => {
  assert.throws(() => validateFilmSpec(null), /object required/);
  assert.throws(() => validateFilmSpec({ id: 'ok', shots: [] }), /non-empty/);
  assert.throws(() => validateFilmSpec({ id: 'BAD ID', shots: [{}] }), /kebab-case/);
  const dup = twoShotSpec(); dup.shots[1].id = 'a';
  assert.throws(() => validateFilmSpec(dup), /duplicate id/);
  const ragged = twoShotSpec(); ragged.shots[1].config.width = 640;
  assert.throws(() => validateFilmSpec(ragged), /uniform/);
  validateFilmSpec(twoShotSpec()); // the valid one passes
});

test('shot cache keys are content-addressed and engine-versioned', () => {
  const k1 = shotCacheKey('scene-source', { a: 1 });
  assert.equal(k1, shotCacheKey('scene-source', { a: 1 }), 'same content -> same key');
  assert.notEqual(k1, shotCacheKey('scene-source-CHANGED', { a: 1 }), 'scene edit busts cache');
  assert.notEqual(k1, shotCacheKey('scene-source', { a: 2 }), 'config edit busts cache');
  assert.match(k1, /^[0-9a-f]{64}$/);
  assert.ok(ENGINE_VERSION.includes('longform'));
});

test('black/freeze segments need timecoded reasons to pass', () => {
  const segs = [{ kind: 'black', start: 0, end: 1.2 }, { kind: 'freeze', start: 40, end: 46 }];
  const ok = checkSegmentsAgainstExceptions(segs, [
    { kind: 'black', from: 0, to: 1.5, reason: 'fade from black' },
    { kind: 'freeze', from: 39.5, to: 46.5, reason: 'intentional hold on final chart' },
  ]);
  assert.deepEqual(ok, []);
  const noReason = checkSegmentsAgainstExceptions(segs, [{ kind: 'black', from: 0, to: 1.5 }]);
  assert.equal(noReason.length, 2, 'an exception without a reason explains nothing');
  const partial = checkSegmentsAgainstExceptions(segs, [{ kind: 'black', from: 0, to: 1.5, reason: 'fade' }]);
  assert.deepEqual(partial, [segs[1]], 'uncovered freeze stays unexplained');
});

test('two real shots render, stitch and pass measured QC; rerun resumes from cache', async () => {
  await workspace(async (dir) => {
    const work = path.join(dir, 'work');
    const progress = [];
    const m1 = await buildFilm({ spec: twoShotSpec(), workDir: work, onProgress: (p) => progress.push(p) });
    assert.equal(m1.shots.length, 2);
    assert.ok(m1.shots.every((s) => s.cache === 'rendered'), 'first run renders both shots');
    assert.ok(Math.abs(m1.final.duration - 4) < 0.3, `final ~4s, got ${m1.final.duration}`);
    assert.equal(m1.final.video.width, 320);
    assert.match(m1.final.sha256, /^[0-9a-f]{64}$/);
    assert.deepEqual(m1.unexplainedSegments, []);
    assert.deepEqual(m1.violations, []);
    assert.ok(progress.some((p) => p.phase === 'concat') && progress.at(-1).phase === 'complete');
    // film manifest on disk is the delivery-facing artifact
    const onDisk = JSON.parse(await readFile(path.join(work, 'film-manifest.json'), 'utf8'));
    assert.equal(onDisk.final.sha256, m1.final.sha256);
    assert.match(onDisk.grading, /not taste|engineering/i);

    // interrupt simulation: rerun the same spec — finished shots must come from
    // cache (no lost or duplicated shots), and the final must be reproducible
    const m2 = await buildFilm({ spec: twoShotSpec(), workDir: work });
    assert.ok(m2.shots.every((s) => s.cache === 'hit'), 'resume renders nothing again');
    assert.deepEqual(m2.shots.map((s) => s.key), m1.shots.map((s) => s.key));
    assert.equal(m2.final.duration, m1.final.duration);
  });
});

test('fail closed: missing scene, broken timing and window violations stop the build', async () => {
  await workspace(async (dir) => {
    const gone = twoShotSpec(); gone.shots[0].scene = 'scenes/nope.mjs';
    await assert.rejects(buildFilm({ spec: gone, workDir: path.join(dir, 'w1') }), /scene file missing/);

    // duration window violation is reported, not silently accepted
    const spec = twoShotSpec(); spec.durationWindow = [300, 330];
    await assert.rejects(buildFilm({ spec, workDir: path.join(dir, 'w2') }), /QC violations[\s\S]*duration 4(\.\d+)?s outside window/);
  });
});

test('probe measures what ffprobe says — no invented numbers', async () => {
  await workspace(async (dir) => {
    const m = await buildFilm({ spec: twoShotSpec(), workDir: path.join(dir, 'w') });
    const p = await probe(m.final.file);
    assert.equal(p.video.codec, 'h264');
    assert.equal(p.video.pixFmt, 'yuv420p');
    assert.ok(Math.abs(p.duration - m.final.duration) < 0.01);
  });
});
