/**
 * quality/lint.mjs (Leonidas, M2 t-20261013-0bd4)
 * "Ban the slop" gate for scene sources. The studio's quality failure
 * mode is the generic AI look: linear tweens, gradient-wash backgrounds,
 * placeholder shapes. These are banned at the source level so a scene
 * cannot silently regress to them; enforcement runs in tests and can
 * run in CI on any scene file.
 *
 * Rules (each returns a named issue, never a vague failure):
 *  - no-linear-easing     'linear' easing/tween usage
 *  - no-gradient-fill     createLinearGradient/createRadialGradient or
 *                         CSS linear-gradient/radial-gradient in source
 *  - no-css-animation     @keyframes / animation: (engine also rejects
 *                         DOM animations at capture time)
 *  - spring-required      scene animates but never imports quality/spring
 */

const RULES = [
  { id: 'no-linear-easing',
    test: src => /(easing|ease|tween)[^;\n]{0,40}['"]linear['"]|['"]linear['"][^;\n]{0,20}(easing|ease)/i.test(src)
      || /\blinearTween\b|\bmakeTween\b/.test(src),
    message: 'linear easing/tween found — animate with quality/spring (integrated springs) instead' },
  { id: 'no-gradient-fill',
    test: src => /create(Linear|Radial)Gradient|(linear|radial)-gradient\(/.test(src),
    message: 'gradient fill found — paint real assets (shapes, type, texture), not gradient wash' },
  { id: 'no-css-animation',
    test: src => /@keyframes|\banimation\s*:/.test(src),
    message: 'CSS animation found — frames must be painted on Canvas at explicit times' },
];

export function lintSceneSource(source, { filename = '<scene>' } = {}) {
  const issues = [];
  for (const rule of RULES) {
    if (rule.test(source)) issues.push({ rule: rule.id, file: filename, message: rule.message });
  }
  const animates = /\b(time|frame)\b/.test(source) && /fillText|fillRect|arc\(|drawImage|beginPath/.test(source);
  if (animates && !/quality\/spring/.test(source)) {
    issues.push({ rule: 'spring-required', file: filename,
      message: 'scene animates without importing quality/spring — motion must come from springs' });
  }
  return issues;
}

export function assertSceneClean(source, opts) {
  const issues = lintSceneSource(source, opts);
  if (issues.length) {
    throw new Error('scene lint failed: ' + issues.map(i => `${i.rule}: ${i.message}`).join('; '));
  }
  return true;
}
