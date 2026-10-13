export function validateConfig(input = {}) {
  const c = { width: 960, height: 540, fps: 24, duration: 4, maxAttempts: 2, threshold: 8, ...input };
  for (const [key,min,max] of [['width',160,1920],['height',90,1080],['fps',1,60],['maxAttempts',1,4]]) {
    if (!Number.isInteger(c[key]) || c[key] < min || c[key] > max) throw new Error(`Invalid ${key}: expected integer ${min}–${max}`);
  }
  if (c.width % 2 || c.height % 2) throw new Error('H.264 dimensions must be even');
  if (!Number.isFinite(c.duration) || c.duration <= 0 || c.duration > 30) throw new Error('Invalid duration');
  if (!Number.isFinite(c.threshold) || c.threshold < 8 || c.threshold > 10) throw new Error('Threshold must be 8–10');
  c.frameCount = Math.round(c.duration * c.fps);
  if (c.frameCount < 2 || c.frameCount > 900) throw new Error('Expected 2–900 frames');
  c.duration = c.frameCount / c.fps;
  const beats = c.beatMap?.beats ?? [], cuts = c.beatMap?.cuts ?? [];
  for (const list of [beats,cuts]) {
    if (!Array.isArray(list) || list.length > 900 || list.some((v,i) => !Number.isFinite(v) || v < 0 || v > c.duration || (i > 0 && v <= list[i-1]))) throw new Error('Beat/cut times must be finite, ascending, within duration');
  }
  c.beatMap = { beats, cuts };
  return c;
}
