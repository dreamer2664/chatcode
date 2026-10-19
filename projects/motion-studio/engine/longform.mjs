// longform.mjs — V02 (t-20261015-fec3): five-minute film orchestration on top
// of the motion-studio single-shot renderer, WITHOUT touching its safety caps.
//
// Design contract (card t-20261015-fec3 + docs/ACCEPTANCE.md):
//   * partition into bounded shots — every shot still passes the engine's own
//     validateConfig (<=30 s, 2–900 frames). We never widen those numbers;
//   * resumable — each shot is content-hash cached (scene source + config +
//     engine version). An interrupted run resumes: finished shots are verified
//     from cache, never re-rendered, never duplicated;
//   * stitched in spec order via ffmpeg concat demuxer (uniform geometry/fps
//     asserted first), narration muxed, captions kept as SRT/VTT sidecars;
//   * fail closed — broken assets, timing drift, loudness/peak violations,
//     black/freeze frames or missing narration stop the run with a timecoded
//     reason. No fabricated quality score: only measured values, plus the
//     engine's own "structural-pass" label, which is engineering, not taste.
//
// Everything here is measurement or orchestration. Artistic approval is the
// two non-owner full-watch reviews, bound to the final SHA-256 — never this file.

import { mkdir, readFile, writeFile, rm, readdir, stat } from 'node:fs/promises';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { renderVideo, ffmpegPath, runProcess, projectRoot } from './render.mjs';

const sha = (b) => createHash('sha256').update(b).digest('hex');
const shaFile = async (p) => sha(await readFile(p));

export const ENGINE_VERSION = 'longform-v1';

// ---------------------------------------------------------------------------
// spec validation — the film spec is the contract between script and machine
// ---------------------------------------------------------------------------
export function validateFilmSpec(spec) {
  if (!spec || typeof spec !== 'object') throw new Error('spec: object required');
  if (!/^[a-z0-9][a-z0-9-]{0,63}$/.test(spec.id || '')) throw new Error('spec.id: kebab-case id required');
  if (!Array.isArray(spec.shots) || spec.shots.length === 0) throw new Error('spec.shots: non-empty array required');
  const seen = new Set();
  for (const s of spec.shots) {
    if (!/^[a-z0-9][a-z0-9-]{0,63}$/.test(s?.id || '')) throw new Error(`shot ${s?.id}: kebab-case id required`);
    if (seen.has(s.id)) throw new Error(`shot ${s.id}: duplicate id`);
    seen.add(s.id);
    if (!s.scene || typeof s.scene !== 'string') throw new Error(`shot ${s.id}: scene path required`);
    if (!s.config || typeof s.config !== 'object') throw new Error(`shot ${s.id}: config required`);
  }
  const first = spec.shots[0].config;
  for (const s of spec.shots) {
    if (s.config.width !== first.width || s.config.height !== first.height || s.config.fps !== first.fps) {
      throw new Error(`shot ${s.id}: geometry/fps must be uniform across the film (concat requires it)`);
    }
  }
  if (spec.narration != null) {
    if (typeof spec.narration !== 'string') throw new Error('spec.narration: path string required when present');
  }
  if (spec.durationWindow != null) {
    const [lo, hi] = spec.durationWindow;
    if (!(Number.isFinite(lo) && Number.isFinite(hi) && 0 < lo && lo <= hi)) throw new Error('spec.durationWindow: [lo,hi] with 0<lo<=hi');
  }
  if (spec.allowRepeatedShots != null) {
    const r = spec.allowRepeatedShots?.reason;
    if (typeof r !== 'string' || r.trim().length < 12) throw new Error('spec.allowRepeatedShots.reason: a real reason is required to ship repeated shots');
  }
  return spec;
}

// ---------------------------------------------------------------------------
// content-hash cache — the resume mechanism
// ---------------------------------------------------------------------------
export function shotCacheKey(sceneSource, config) {
  return sha(JSON.stringify({ engine: ENGINE_VERSION, scene: sha(sceneSource), config }));
}

async function cachedShot(cacheDir, key) {
  const dir = path.join(cacheDir, key);
  const mp4 = path.join(dir, 'film.mp4');
  const manifest = path.join(dir, 'manifest.json');
  try {
    const st = await stat(mp4);
    if (st.size === 0) return null;
    const m = JSON.parse(await readFile(manifest, 'utf8'));
    // a shot that failed grading (or was cancelled mid-render) is not resumable evidence
    if (m.status !== 'structural-pass' && m.status !== 'provider-approved') return null;
    return { mp4, manifest: m, dir };
  } catch { return null; }
}

// ---------------------------------------------------------------------------
// ffprobe helpers — every claim about media here is a measurement
// ---------------------------------------------------------------------------
export async function probe(file) {
  const { stdout } = await runProcess(process.env.FFPROBE_PATH || ffmpegPath.replace(/ffmpeg$/, 'ffprobe'),
    ['-v', 'error', '-print_format', 'json', '-show_format', '-show_streams', file]);
  const j = JSON.parse(stdout);
  const v = j.streams.find((s) => s.codec_type === 'video');
  const a = j.streams.find((s) => s.codec_type === 'audio');
  return {
    duration: Number(j.format.duration),
    size: Number(j.format.size),
    video: v && { codec: v.codec_name, width: Number(v.width), height: Number(v.height), fps: v.r_frame_rate, pixFmt: v.pix_fmt, frames: v.nb_frames != null ? Number(v.nb_frames) : null },
    audio: a && { codec: a.codec_name, sampleRate: Number(a.sample_rate), channels: a.channels, bitRate: a.bit_rate != null ? Number(a.bit_rate) : null },
  };
}

export async function fullDecodeCheck(file) {
  // full-file decode: every frame must survive, not just the first
  const { stderr } = await runProcess(ffmpegPath, ['-v', 'error', '-xerror', '-i', file, '-f', 'null', '-']);
  return { ok: stderr.trim() === '', errors: stderr.trim() };
}

export async function loudness(file) {
  // integrated loudness + true peak via ebur128 (single pass, honest numbers)
  const { stderr } = await runProcess(ffmpegPath, ['-hide_banner', '-nostats', '-i', file, '-filter_complex', 'ebur128=peak=true', '-f', 'null', '-']);
  const tail = stderr.split('\n').slice(-14).join('\n');
  const I = /I:\s*(-?[\d.]+)\s*LUFS/.exec(tail);
  const P = /Peak:\s*(-?[\d.]+)\s*dBFS/.exec(tail.split('True peak:')[1] || tail);
  if (!I) throw new Error(`loudness: could not parse ebur128 summary:\n${tail}`);
  return { integratedLufs: Number(I[1]), truePeakDbfs: P ? Number(P[1]) : null };
}

export async function blackFreeze(file, { blackMin = 0.5, freezeMin = 4 } = {}) {
  const { stderr } = await runProcess(ffmpegPath, ['-hide_banner', '-i', file, '-vf',
    `blackdetect=d=${blackMin}:pix_th=0.10,freezedetect=n=-55dB:d=${freezeMin}`, '-an', '-f', 'null', '-']);
  const segs = [];
  for (const line of stderr.split('\n')) {
    let m = /blackdetect\] black_start:([\d.]+) black_end:([\d.]+)/.exec(line);
    if (m) segs.push({ kind: 'black', start: Number(m[1]), end: Number(m[2]) });
    m = /freezedetect\] freeze_start:([\d.]+) freeze_end:([\d.]+)/.exec(line);
    if (m) segs.push({ kind: 'freeze', start: Number(m[1]), end: Number(m[2]) });
  }
  return segs;
}

// timecoded intentional exceptions: [{kind:'black'|'freeze', from, to, reason}]
export function checkSegmentsAgainstExceptions(segs, exceptions = [], tolerance = 0.5) {
  const unexplained = [];
  for (const s of segs) {
    const ok = exceptions.some((e) => e.kind === s.kind && e.reason && s.start >= e.from - tolerance && s.end <= e.to + tolerance);
    if (!ok) unexplained.push(s);
  }
  return unexplained;
}

// ---------------------------------------------------------------------------
// render one shot (or take it from cache) — the resumable unit
// ---------------------------------------------------------------------------
export async function renderShot({ shot, cacheDir, outRoot, signal, onProgress }) {
  // resolve against projectRoot exactly like renderVideo does, so the cache key
  // hashes the same bytes the renderer will actually execute
  const scenePath = path.resolve(projectRoot, shot.scene);
  if (!scenePath.startsWith(projectRoot + path.sep)) throw new Error(`shot ${shot.id}: scene must be inside the project`);
  const source = await readFile(scenePath).catch(() => {
    throw new Error(`shot ${shot.id}: scene file missing: ${shot.scene}`);
  });
  const key = shotCacheKey(source, shot.config);
  const hit = await cachedShot(cacheDir, key);
  if (hit) return { ...hit, key, cache: 'hit' };

  const outDir = path.join(cacheDir, key);
  await rm(outDir, { recursive: true, force: true }); // never resume from a half-written shot
  await mkdir(outDir, { recursive: true });
  const result = await renderVideo({ outputDir: outDir, config: shot.config, scene: shot.scene, signal, onProgress });
  const mp4 = result.videoPath;
  try { await stat(mp4); } catch { throw new Error(`shot ${shot.id}: renderer finished but produced no video at ${mp4}`); }
  const manifest = result.manifest;
  // scratch cleanup: PNG frames are intermediate — the encoded shot + manifest
  // are the resumable evidence. 1080p frames are ~2 MB each; keeping them for
  // every shot of a five-minute film would fill the disk mid-run.
  await rm(path.join(outDir, 'frames'), { recursive: true, force: true });
  return { mp4, manifest, dir: outDir, key, cache: 'rendered', result };
}

// ---------------------------------------------------------------------------
// the orchestrator
// ---------------------------------------------------------------------------
export async function buildFilm({ spec, workDir, cacheDir, signal, onProgress = () => {}, exceptions = [] }) {
  const t0 = Date.now();
  validateFilmSpec(spec);
  workDir = path.resolve(workDir); cacheDir = path.resolve(cacheDir || path.join(workDir, 'shot-cache'));
  await mkdir(workDir, { recursive: true }); await mkdir(cacheDir, { recursive: true });
  const qc = { shots: [], unexplainedSegments: [], violations: [] };

  // 1) shots — bounded, cached, in order ----------------------------------
  const shotFiles = [];
  for (const shot of spec.shots) {
    onProgress({ phase: 'shot', shot: shot.id });
    const r = await renderShot({ shot, cacheDir, outRoot: workDir, signal, onProgress });
    const p = await probe(r.mp4);
    const expected = shot.config.duration;
    if (Math.abs(p.duration - expected) > 1 / shot.config.fps + 0.05) {
      throw new Error(`shot ${shot.id}: timing broken — expected ${expected}s, got ${p.duration}s (fail closed, no stretching)`);
    }
    if (p.video.width !== shot.config.width || p.video.height !== shot.config.height) {
      throw new Error(`shot ${shot.id}: geometry broken — ${p.video.width}x${p.video.height} != ${shot.config.width}x${shot.config.height}`);
    }
    shotFiles.push(r.mp4);
    qc.shots.push({ id: shot.id, key: r.key, cache: r.cache, file: r.mp4, sha256: await shaFile(r.mp4), duration: p.duration, expected });
  }

  // 1b) filler/loop guard — repeated identical shots are a fixture, not a film.
  // Calibration run A (twelve byte-identical demo shots, same cache key) is
  // exactly what this refuses; ACCEPTANCE forbids padding with repeated
  // material, so the rig must refuse it too instead of reporting qc-pass.
  const byHash = new Map();
  for (const s of qc.shots) {
    if (byHash.has(s.sha256)) {
      const reason = spec.allowRepeatedShots?.reason;
      if (!reason) throw new Error(`filler/loop guard: shots '${byHash.get(s.sha256)}' and '${s.id}' are byte-identical (sha256 ${s.sha256.slice(0, 16)}…). Repeated material is filler, not a film — vary the shots, or record spec.allowRepeatedShots.reason.`);
      qc.repeatedShotsAllowed = reason;
    } else byHash.set(s.sha256, s.id);
  }

  // 2) concat — demuxer, no re-encode (all shots asserted uniform above) ----
  onProgress({ phase: 'concat' });
  const listFile = path.join(workDir, 'concat.txt');
  await writeFile(listFile, shotFiles.map((f) => `file '${f.replace(/'/g, `'\\''`)}'`).join('\n') + '\n');
  const videoOnly = path.join(workDir, 'video-only.mp4');
  await runProcess(ffmpegPath, ['-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', listFile, '-c', 'copy', videoOnly]);
  const pv = await probe(videoOnly);
  const expectedTotal = spec.shots.reduce((s, x) => s + x.config.duration, 0);
  if (Math.abs(pv.duration - expectedTotal) > 0.5) {
    throw new Error(`concat: total ${pv.duration}s != sum of shots ${expectedTotal}s (stitching lost or duplicated material)`);
  }

  // 3) narration mux (when the spec carries a narration track) --------------
  let finalVideo = videoOnly;
  const finalFile = path.join(workDir, `${spec.id}-final.mp4`);
  if (spec.narration) {
    onProgress({ phase: 'mux' });
    const narration = path.resolve(spec.narration);
    const pa = await probe(narration);
    if (pa.audio == null) throw new Error('narration: file has no audio stream');
    const drift = pa.duration - pv.duration;
    if (Math.abs(drift) > 1.0) throw new Error(`narration: A/V drift ${drift.toFixed(3)}s exceeds 1.0s tolerance — fix the cut or the track, never pad`);
    await runProcess(ffmpegPath, ['-y', '-v', 'error', '-i', videoOnly, '-i', narration,
      '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest', finalFile]);
    qc.narration = { file: narration, sha256: await shaFile(narration), duration: pa.duration, drift };
  } else {
    await runProcess(ffmpegPath, ['-y', '-v', 'error', '-i', videoOnly, '-c', 'copy', finalFile]);
  }
  finalVideo = finalFile;

  // 4) QC — measured, fail closed -------------------------------------------
  onProgress({ phase: 'qc' });
  const pf = await probe(finalVideo);
  const decode = await fullDecodeCheck(finalVideo);
  if (!decode.ok) throw new Error(`QC: full-file decode failed: ${decode.errors.slice(0, 400)}`);
  const segs = await blackFreeze(finalVideo);
  qc.unexplainedSegments = checkSegmentsAgainstExceptions(segs, exceptions);
  if (qc.unexplainedSegments.length) {
    throw new Error(`QC: ${qc.unexplainedSegments.length} unexplained black/freeze segment(s): ${JSON.stringify(qc.unexplainedSegments.slice(0, 5))}`);
  }
  if (spec.durationWindow) {
    const [lo, hi] = spec.durationWindow;
    if (pf.duration < lo || pf.duration > hi) qc.violations.push(`duration ${pf.duration}s outside window [${lo},${hi}]`);
  }
  if (spec.narration) {
    const l = await loudness(finalVideo);
    qc.loudness = l;
    if (Math.abs(l.integratedLufs - (-16)) > 1.5) qc.violations.push(`integrated loudness ${l.integratedLufs} LUFS outside -16 ±1.5`);
    if (l.truePeakDbfs != null && l.truePeakDbfs > -1) qc.violations.push(`true peak ${l.truePeakDbfs} dBFS above -1 dBTP`);
    if (pf.audio?.sampleRate !== 48000) qc.violations.push(`audio sample rate ${pf.audio?.sampleRate} != 48000`);
  }
  if (qc.violations.length) throw new Error(`QC violations (fail closed):\n  ${qc.violations.join('\n  ')}`);

  // 5) manifest + receipts ---------------------------------------------------
  const manifest = {
    engine: ENGINE_VERSION, specId: spec.id, builtAt: new Date().toISOString(),
    final: { file: finalVideo, sha256: await shaFile(finalVideo), size: pf.size, duration: pf.duration, video: pf.video, audio: pf.audio },
    grading: 'measured engineering QC only; artistic approval = two non-owner full-watch reviews bound to final.sha256',
    ...qc,
    receipts: { wallSeconds: (Date.now() - t0) / 1000, node: process.version, ffmpeg: ffmpegPath },
  };
  await writeFile(path.join(workDir, 'film-manifest.json'), JSON.stringify(manifest, null, 2) + '\n');
  onProgress({ phase: 'complete', status: qc.violations.length ? 'violations' : 'qc-pass' });
  return manifest;
}
