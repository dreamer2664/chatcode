#!/usr/bin/env node
// build.mjs — CLI for the long-form orchestrator (V02, t-20261015-fec3).
//   node longform/build.mjs --spec longform/calib-300a.spec.json --work /tmp/film-a
// Env: FFMPEG_PATH / FFPROBE_PATH (system builds preferred), LD_LIBRARY_PATH
// for rootless chromium (see ytlab/tools/bootstrap-ffmpeg.sh).
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { buildFilm } from '../engine/longform.mjs';

const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => {
  if (v.startsWith('--')) a.push([v.slice(2), arr[i + 1]]); return a;
}, []));
if (!args.spec || !args.work) {
  console.error('usage: node longform/build.mjs --spec <spec.json> --work <dir> [--cache <dir>]');
  process.exit(2);
}
const spec = JSON.parse(await readFile(path.resolve(args.spec), 'utf8'));
const exceptions = args.exceptions ? JSON.parse(await readFile(path.resolve(args.exceptions), 'utf8')) : [];
const t0 = Date.now();
try {
  const m = await buildFilm({ spec, workDir: args.work, cacheDir: args.cache, exceptions,
    onProgress: (p) => console.log(JSON.stringify({ ...p, t: ((Date.now() - t0) / 1000).toFixed(1) })) });
  console.log(JSON.stringify({ status: 'qc-pass', final: m.final.file, sha256: m.final.sha256, duration: m.final.duration, wallSeconds: m.receipts.wallSeconds }));
} catch (e) {
  console.error('FAIL CLOSED:', e.message);
  process.exit(1);
}
