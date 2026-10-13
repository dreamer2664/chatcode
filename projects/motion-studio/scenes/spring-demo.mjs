/**
 * scenes/spring-demo.mjs (Leonidas, M2 t-20261013-0bd4)
 * Demo scene on Achilles' M1 seam. Everything moves on integrated
 * springs (quality/spring), composition changes ONLY on beat cuts
 * (quality/beat), and a critic patch visibly re-renders with more
 * emphasis. Paints real vector assets — skyline, sun, waveform —
 * on a solid ground. Deterministic in (frame, time, patch).
 */
import { springAt, springParams } from '../quality/spring.mjs';
import { makeBeatMap, cutAt, beatIndexAt } from '../quality/beat.mjs';

const INK = '#f2ead8', PAPER = '#182420', ACCENT = '#e07840', ACCENT2 = '#7fb069', SKY = '#2e4a3e';
const titleSpring = springParams({ stiffness: 90, zeta: 0.42 });
const popSpring = springParams({ stiffness: 140, zeta: 0.5 });

function letters(ctx, text, cx, y, t, amp) {
  ctx.save();
  ctx.font = 'bold 54px Georgia, serif';
  ctx.textAlign = 'left';
  const adv = 34;
  let x = cx - (text.length * adv) / 2;
  [...text].forEach((ch, i) => {
    const local = Math.max(0, t - i * 0.07);
    const dy = Math.max(springAt({ ...titleSpring, from: -60, to: 0 }, local) * amp, 96 - y); // enter, never clip
    ctx.fillStyle = i % 5 === 3 ? ACCENT : INK;
    ctx.fillText(ch, x, y + dy);
    x += adv;
  });
  ctx.restore();
}

function skyline(ctx, w, base, t, amp) {
  ctx.save();
  ctx.fillStyle = '#101a15';
  const heights = [120, 190, 150, 230, 170, 205, 135, 185];
  heights.forEach((bh, i) => {
    const bw = w / heights.length;
    const rise = springAt({ ...popSpring, from: 0.2, to: 1 }, Math.max(0, t - i * 0.05));
    ctx.fillRect(i * bw, base - bh * rise * amp, bw - 6, bh * rise * amp);
    ctx.fillStyle = ACCENT2;
    for (let wy = 0; wy < 4; wy++) for (let wx = 0; wx < 2; wx++) {
      if ((i * 7 + wy * 3 + wx) % 3) ctx.fillRect(i * bw + 14 + wx * 22, base - bh * rise * amp + 18 + wy * 26, 9, 12);
    }
    ctx.fillStyle = '#101a15';
  });
  ctx.restore();
}

export function render(ctx, { width: w, height: h, time: t, duration, beatMap, patch }) {
  const beatMap2 = beatMap && beatMap.beats && beatMap.beats.length
    ? beatMap : makeBeatMap({ bpm: 120, duration, cutEveryBeats: 2 });
  const amp = 1 + (patch?.emphasis ?? 0) * 0.7;
  const sx = w / 960, sy = h / 540;
  ctx.scale(sx, sy);

  ctx.fillStyle = PAPER; ctx.fillRect(0, 0, 960, 540);
  ctx.fillStyle = 'rgba(242,234,216,0.05)';
  for (let gx = 24; gx < 960; gx += 48) for (let gy = 24; gy < 540; gy += 48) {
    ctx.beginPath(); ctx.arc(gx, gy, 1.6, 0, 2 * Math.PI); ctx.fill();
  }

  const section = cutAt(beatMap2, t) % 4;
  const localT = t - (beatMap2.cuts[cutAt(beatMap2, t)] ?? 0);
  ctx.fillStyle = INK; ctx.font = '13px sans-serif';
  ctx.fillText('MOTION BY CODE — SPRING STUDY', 44, 44);
  ctx.textAlign = 'right'; ctx.fillText(`BEAT ${beatIndexAt(beatMap2, t) + 1}`, 916, 44); ctx.textAlign = 'left';

  if (section === 0) {
    // Open rich, not empty: panel, skyline, big sun from the first frame
    // (a near-blank opener fails every honest gate, including ours).
    const s = springAt({ ...popSpring, from: 0.55, to: 1 }, localT);
    ctx.fillStyle = SKY; ctx.fillRect(44, 80, 872, 330);
    skyline(ctx, 960, 410, localT, amp);
    ctx.fillStyle = ACCENT;
    ctx.beginPath(); ctx.arc(480, 225, 92 * s * amp, 0, 2 * Math.PI); ctx.fill();
    ctx.strokeStyle = INK; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(480, 225, 118 * s, 0, 2 * Math.PI); ctx.stroke();
    ctx.fillStyle = '#e8b34b';
    ctx.beginPath(); ctx.arc(160, 140, 26 * s, 0, 2 * Math.PI); ctx.fill();
    ctx.beginPath(); ctx.arc(800, 140, 26 * s, 0, 2 * Math.PI); ctx.fill();
    letters(ctx, 'GRAVITY', 480, 480, localT, amp);
  } else if (section === 1) {
    const beatStart = beatMap2.beats[beatIndexAt(beatMap2, t)] ?? 0;
    ctx.fillStyle = SKY; ctx.fillRect(44, 90, 872, 320);
    ctx.strokeStyle = 'rgba(242,234,216,0.25)'; ctx.lineWidth = 1;
    for (let i = 0; i <= 8; i++) { ctx.beginPath(); ctx.moveTo(44 + i * 109, 90); ctx.lineTo(44 + i * 109, 410); ctx.stroke(); }
    ctx.fillStyle = 'rgba(242,234,216,0.16)'; ctx.fillRect(44, 330, 872, 3);
    for (let i = 0; i < 16; i++) {
      const target = 90 + ((i * 53) % 190);
      const v = springAt({ ...popSpring, from: 0.25, to: 1 }, Math.max(0, t - beatStart - i * 0.012));
      ctx.fillStyle = i % 4 === 0 ? ACCENT : ACCENT2;
      ctx.fillRect(80 + i * 51, 333 - target * v * amp, 30, target * v * amp);
      ctx.fillRect(80 + i * 51, 333, 30, target * v * amp * 0.35); // reflection mass
    }
    letters(ctx, 'ON THE BEAT', 480, 165, localT, amp);
  } else if (section === 2) {
    const s = springAt({ ...popSpring, from: 0.1, to: 1 }, localT);
    ctx.fillStyle = SKY; ctx.fillRect(44, 90, 872, 300);
    ctx.fillStyle = '#e8b34b';
    ctx.beginPath(); ctx.arc(44 + 800 * s, 150, 34 * amp, 0, 2 * Math.PI); ctx.fill();
    skyline(ctx, 960, 390, localT, amp);
    letters(ctx, 'REAL ASSETS', 480, 480, localT, amp);
  } else {
    const s = springAt({ ...titleSpring, from: 0, to: 1 }, localT);
    ctx.fillStyle = SKY; ctx.fillRect(44, 80, 872, 330);
    ctx.strokeStyle = 'rgba(242,234,216,0.35)'; ctx.lineWidth = 2;
    for (const r of [150, 185, 220]) { ctx.beginPath(); ctx.arc(480, 235, r * s, 0, 2 * Math.PI); ctx.stroke(); }
    skyline(ctx, 960, 410, localT, amp);
    ctx.save(); ctx.translate(480, 235); ctx.rotate((1 - s) * 0.6);
    ctx.fillStyle = ACCENT; ctx.fillRect(-90, -90, 180, 180);
    ctx.fillStyle = PAPER; ctx.font = 'bold 92px Georgia, serif'; ctx.textAlign = 'center';
    ctx.fillText('M', 0, 34); ctx.restore(); ctx.textAlign = 'left';
    ctx.fillStyle = ACCENT2; ctx.fillRect(330, 428, 300 * s, 6);
    letters(ctx, 'SETTLED', 480, 498, localT, amp);
  }

  // Drifting particles keep settled springs honestly alive (not dead frames).
  ctx.fillStyle = 'rgba(242,234,216,0.55)';
  for (let i = 0; i < 14; i++) {
    const px = (i * 173 + t * (9 + i * 2) * amp) % 960;
    const py = 90 + ((i * 97) % 380) + Math.sin(t * 1.4 + i) * 9;
    ctx.beginPath(); ctx.arc(px, py, 2.4, 0, 2 * Math.PI); ctx.fill();
  }
  ctx.fillStyle = 'rgba(242,234,216,0.7)'; ctx.font = '12px sans-serif';
  ctx.fillText('CODE -> FRAMES -> FILM', 44, 512);
  return { intentionalHold: false };
}
