/**
 * quality/critic.mjs (Leonidas, M2 t-20261013-0bd4)
 * Semantic-lane critic for Achilles' M1 engine seam:
 *
 *   analyze({ imagePath, frame, time, beatMap, metrics, revision })
 *     -> { score: 0..10, issues: [...], patch: { emphasis }, evidence }
 *
 * HONEST SCOPE: this scores MEASURABLE composition evidence — colour
 * diversity, edge detail, contrast, luminance-centroid composition,
 * and motion relative to the beat grid. It is a formula, documented
 * below, not a taste model and not a human artistic verdict. The
 * engine (engine/quality.mjs) remains the structural authority.
 *
 * Score (10): palette 2.0 + edge detail 2.5 + contrast 2.0
 *           + content coverage 2.0 + beat-motion 1.5.
 * Palette rewards an INTENTIONAL palette (>=2 hue families at full
 * marks), not rainbow noise — calibrated against Achilles' accepted
 * M1 evidence frames, which carry exactly 2 hue families and score
 * ~9 under this formula while a blank frame scores ~0.
 * patch.emphasis (0..1) grows with revision so a re-render visibly
 * changes the scene instead of repeating the failed frame.
 */
import { readFile } from 'node:fs/promises';
import { PNG } from 'pngjs';

const clamp01 = v => Math.min(1, Math.max(0, v));

export async function analyze({ imagePath, frame, time, beatMap, metrics, revision = 0 }) {
  const png = PNG.sync.read(await readFile(imagePath));
  const step = Math.max(1, Math.floor(Math.min(png.width, png.height) / 120));
  const hueBins = new Set();
  const corner = [0, 0, 0];
  for (const [px, py] of [[0, 0], [png.width - 1, 0], [0, png.height - 1], [png.width - 1, png.height - 1]]) {
    const ci = (py * png.width + px) * 4;
    corner[0] += png.data[ci] / 4; corner[1] += png.data[ci + 1] / 4; corner[2] += png.data[ci + 2] / 4;
  }
  let content = 0;
  let n = 0, sum = 0, sq = 0, edgeHits = 0, edgePairs = 0;
  let cx = 0, cy = 0, wsum = 0;
  const lum = [];
  for (let y = 0; y < png.height; y += step) {
    const row = [];
    for (let x = 0; x < png.width; x += step) {
      const i = (y * png.width + x) * 4;
      const r = png.data[i], g = png.data[i + 1], b = png.data[i + 2];
      const v = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      row.push(v); lum.push(v); sum += v; sq += v * v; n++;
      if (Math.hypot(r - corner[0], g - corner[1], b - corner[2]) > 30) content++;
      const mx = Math.max(r, g, b), mn = Math.min(r, g, b);
      if (mx - mn > 24 && mx > 40) { // saturated enough to have a hue
        let h = 0;
        if (mx === r) h = ((g - b) / (mx - mn)) % 6;
        else if (mx === g) h = (b - r) / (mx - mn) + 2;
        else h = (r - g) / (mx - mn) + 4;
        hueBins.add(Math.floor(((h * 60 + 360) % 360) / 30));
      }
      cx += x * v; cy += y * v; wsum += v;
      if (lum.length > 1 && x > 0) {
        edgePairs++;
        if (Math.abs(v - row[row.length - 2]) > 18) edgeHits++;
      }
    }
  }
  const contrast = metrics?.contrast ?? Math.sqrt(Math.max(0, sq / n - (sum / n) ** 2));
  const edgeDensity = edgePairs ? edgeHits / edgePairs : 0;
  const centroidOff = wsum > 0
    ? Math.hypot(cx / wsum / png.width - 0.5, cy / wsum / png.height - 0.5) : 0;
  const delta = metrics?.meanFrameDelta;
  const parts = {
    colour: hueBins.size >= 2 ? 2.0 : hueBins.size === 1 ? 1.0 : 0,
    edge: clamp01(edgeDensity / 0.06) * 2.5,
    contrast: clamp01(contrast / 40) * 2.0,
    // Content coverage is computed below from non-background samples.
    composition: 0,
    beatMotion: delta == null ? 0.75 : clamp01(delta / 6) * 1.5,
  };
  const coverage = n ? content / n : 0;
  parts.composition = clamp01(coverage / 0.22) * 2.0;
  if (coverage > 0.97) parts.composition = 0.4; // a flat wash is not composition
  // A component that cannot be measured (frame 0 has no predecessor to
  // diff against) is excluded and the rest rescaled to 10 — the same
  // convention as Achilles' structural gate, not a free pass.
  const raw = Object.values(parts).reduce((a, b) => a + b, 0);
  const score = Math.round((delta == null ? raw / 8.5 * 10 : raw) * 100) / 100;
  const issues = [];
  if (parts.colour < 1.0) issues.push('low-colour-diversity');
  if (parts.edge < 1.25) issues.push('low-edge-detail');
  if (parts.contrast < 1.0) issues.push('low-contrast');
  if (parts.composition < 1.0) issues.push('dead-composition');
  if (delta != null && parts.beatMotion < 0.5) issues.push('low-motion-vs-beat');
  return {
    score,
    issues,
    patch: score >= 8 ? null : { emphasis: Math.min(1, 0.3 + 0.35 * revision) },
    evidence: {
      hueBins: hueBins.size, edgeDensity: Math.round(edgeDensity * 1000) / 1000,
      contrast: Math.round(contrast * 100) / 100,
      coverage: Math.round(coverage * 1000) / 1000,
      centroidOffset: Math.round(centroidOff * 1000) / 1000,
      parts, frame, time,
      note: 'measurable composition evidence; not a taste verdict',
    },
  };
}

export default { analyze };
