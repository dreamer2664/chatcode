/** Original vector calibration reel. Deterministic; NOT the final spring/beat design. */
export function render(ctx,{width:w,height:h,time:t,frame,fps,duration}) {
  const sx=w/960,sy=h/540;
  ctx.scale(sx,sy);
  ctx.fillStyle='#eeeadd';ctx.fillRect(0,0,960,540);
  ctx.strokeStyle='#d9d4c7';ctx.lineWidth=.6;
  for(let x=32;x<960;x+=32){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,540);ctx.stroke();}
  for(let y=28;y<540;y+=32){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(960,y);ctx.stroke();}
  ctx.fillStyle='#1e2822';ctx.font='12px sans-serif';ctx.fillText('FIELDNOTES  /  MOTION STUDIES',48,45);
  ctx.textAlign='right';ctx.fillText('01 — THE ORBIT',912,45);ctx.textAlign='left';
  ctx.fillStyle='#222923';ctx.font='bold 64px Georgia, serif';
  const drift=3*Math.sin(t*1.3);
  ctx.fillText('Give ideas',48+drift,214);ctx.fillText('a little gravity.',48-drift,288);
  ctx.font='15px sans-serif';ctx.fillStyle='#657065';ctx.fillText('A frame is a decision. Make every one count.',51,333);
  ctx.save();ctx.translate(720,264);ctx.rotate(t*.27);
  ctx.strokeStyle='#313a2f';ctx.lineWidth=1.2;
  for(let r=130;r<=155;r+=12){ctx.beginPath();ctx.arc(0,0,r,0,2*Math.PI);ctx.stroke();}
  for(let i=0;i<9;i++){
    ctx.save();ctx.rotate(i*2*Math.PI/9);ctx.fillStyle=i%2?'#cf7448':'#db8352';
    ctx.beginPath();ctx.moveTo(19,-20);ctx.bezierCurveTo(145,-105,160,-12,89,35);ctx.bezierCurveTo(47,71,-16,56,19,-20);ctx.fill();
    ctx.strokeStyle='#87452c';ctx.lineWidth=1;ctx.stroke();ctx.restore();
  }
  ctx.fillStyle='#eeeadd';ctx.beginPath();ctx.arc(0,0,25,0,2*Math.PI);ctx.fill();
  ctx.strokeStyle='#303e34';ctx.beginPath();ctx.arc(0,0,17,0,2*Math.PI);ctx.stroke();
  ctx.restore();
  const orbit=t*.8;
  ctx.fillStyle='#293c2f';ctx.beginPath();ctx.arc(720+174*Math.cos(orbit),264+174*Math.sin(orbit),7,0,2*Math.PI);ctx.fill();
  ctx.fillStyle='#222923';ctx.font='12px sans-serif';ctx.fillText('CODE → FRAMES → FILM',48,491);
  ctx.textAlign='right';ctx.fillStyle='#657065';ctx.fillText(`${String(frame).padStart(4,'0')} / ${Math.round(duration*fps)}   •   ${t.toFixed(2)}s`,912,491);ctx.textAlign='left';
  ctx.fillStyle='#cf7448';ctx.fillRect(48,514,864*(t/duration),3);
  return {intentionalHold:false};
}
