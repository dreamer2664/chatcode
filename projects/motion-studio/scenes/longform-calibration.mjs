/** ENGINEERING CALIBRATION SCENE — V02 long-form rig, NOT an editorial film.
 *  Deterministic and visibly distinct per shot (large shot number, varying
 *  palette and sweep), so a repeated/looped calibration film is obvious to a
 *  human reviewer and differs per shot in the render manifest. The card is
 *  labelled on every frame. */
const PALETTES = [
  ['#eeeadd', '#1e2822', '#cf7448', '#313a2f'],
  ['#e6ecf2', '#16222e', '#3f7fb5', '#2b3d4d'],
  ['#f0e6ea', '#2c1a22', '#b4567a', '#4a3140'],
  ['#e8eee4', '#1d2a1a', '#6f9a4a', '#33452c'],
  ['#f2ece0', '#2a2418', '#c79a3a', '#4a4030'],
  ['#e4eaec', '#182426', '#3f9a9a', '#2c4346'],
];

export function render(ctx, { width: w, height: h, time: t, frame, fps, duration, calibVariant = 0 }) {
  const variant = Number(calibVariant) || 0;
  const [bg, ink, accent, dark] = PALETTES[variant % PALETTES.length];
  ctx.scale(w / 960, h / 540);
  ctx.fillStyle = bg; ctx.fillRect(0, 0, 960, 540);

  ctx.strokeStyle = dark; ctx.lineWidth = 0.6;
  for (let x = 32; x < 960; x += 32) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, 540); ctx.stroke(); }
  for (let y = 28; y < 540; y += 32) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(960, y); ctx.stroke(); }

  ctx.fillStyle = ink; ctx.font = '12px sans-serif';
  ctx.fillText('ENGINEERING CALIBRATION FIXTURE — NOT AN EDITORIAL FILM', 48, 45);
  ctx.textAlign = 'right';
  ctx.fillText(`SHOT ${String(variant + 1).padStart(2, '0')} / 12   •   V02 LONG-FORM RIG`, 912, 45);
  ctx.textAlign = 'left';

  // the big shot number: the loop-check's visual proof
  ctx.font = 'bold 190px Georgia, serif'; ctx.fillStyle = accent;
  ctx.fillText(String(variant + 1).padStart(2, '0'), 48, 300);

  // a sweep that differs per shot, so motion is shot-specific too
  const phase = (t / duration) * Math.PI * 2 + variant * 0.7;
  ctx.save(); ctx.translate(720, 264);
  ctx.strokeStyle = dark; ctx.lineWidth = 1.4;
  ctx.beginPath(); ctx.arc(0, 0, 140, 0, Math.PI * 2); ctx.stroke();
  ctx.strokeStyle = accent; ctx.lineWidth = 8;
  ctx.beginPath(); ctx.arc(0, 0, 140, phase, phase + Math.PI * (0.4 + variant * 0.08)); ctx.stroke();
  ctx.fillStyle = ink; ctx.font = '14px sans-serif'; ctx.textAlign = 'center';
  ctx.fillText('25 s / 750 frames', 0, 6);
  ctx.restore(); ctx.textAlign = 'left';

  ctx.fillStyle = ink; ctx.font = '12px sans-serif';
  ctx.fillText('BOUNDED SHOT — 30 s / 900-FRAME CAP PRESERVED', 48, 491);
  ctx.textAlign = 'right'; ctx.fillStyle = dark;
  ctx.fillText(`${String(frame).padStart(4, '0')} / ${Math.round(duration * fps)}   •   ${t.toFixed(2)}s`, 912, 491);
  ctx.textAlign = 'left';
  ctx.fillStyle = accent; ctx.fillRect(48, 514, 864 * (t / duration), 3);
  return { intentionalHold: false };
}
