import { PNG } from 'pngjs';

/** Measurable engineering checks. This is NOT a taste/aesthetic scoring model. */
export function analyzePNG(buffer, previous, { width, height, intentionalHold = false }) {
  const png = PNG.sync.read(buffer);
  const histogram = new Array(32).fill(0);
  const samples = []; let sum = 0, sq = 0, opaque = 0;
  const step = Math.max(1, Math.floor(Math.min(png.width, png.height) / 90));
  for (let y = 0; y < png.height; y += step) for (let x = 0; x < png.width; x += step) {
    const i = (y * png.width + x) * 4;
    const v = .2126 * png.data[i] + .7152 * png.data[i + 1] + .0722 * png.data[i + 2];
    histogram[Math.min(31, Math.floor(v / 8))]++; samples.push(v);
    sum += v; sq += v * v; if (png.data[i + 3] === 255) opaque++;
  }
  const n = samples.length, contrast = Math.sqrt(Math.max(0, sq / n - (sum / n) ** 2));
  const entropy = -histogram.reduce((s, count) => count ? s + count / n * Math.log2(count / n) : s, 0);
  const diversity = histogram.filter(v => v > 0).length;
  const delta = previous && previous.length === n ? samples.reduce((s,v,i) => s + Math.abs(v - previous[i]), 0) / n : null;
  const checks = {
    dimensions: png.width === width && png.height === height,
    opaque: opaque / n > .999,
    contrast: contrast >= 12,
    detail: entropy >= .4 && diversity >= 4,
    notDead: delta === null || delta >= .008 || intentionalHold,
  };
  const issues = Object.entries(checks).filter(([,pass]) => !pass).map(([name]) => name);
  return { score: 2 * Object.values(checks).filter(Boolean).length, issues,
    metrics: { contrast, entropy, diversity, meanLuminance: sum/n, meanFrameDelta: delta }, samples, checks };
}

export function decideQuality(structural, semantic, threshold = 8) {
  if (!Number.isFinite(threshold) || threshold < 0 || threshold > 10) throw new Error('Invalid threshold');
  if (semantic && (!Number.isFinite(semantic.score) || semantic.score < 0 || semantic.score > 10)) throw new Error('Critic returned invalid score');
  // Blank/malformed frames cannot pass simply by collecting unrelated points.
  const fatal = !structural.checks.dimensions || !structural.checks.opaque || !structural.checks.contrast || !structural.checks.detail || !structural.checks.notDead;
  const passed = !fatal && structural.score >= threshold && (!semantic || semantic.score >= threshold);
  return { passed, structuralScore: structural.score, semanticScore: semantic?.score ?? null,
    semanticReview: semantic ? (semantic.score >= threshold ? 'provider-pass' : 'provider-fail') : 'not-provided',
    issues: [...structural.issues, ...(semantic?.issues ?? [])] };
}
