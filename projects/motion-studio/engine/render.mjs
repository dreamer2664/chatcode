import { chromium } from 'playwright';
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { validateConfig } from './config.mjs';
import { analyzePNG, decideQuality } from './quality.mjs';

const require = createRequire(import.meta.url);
export const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
export const ffmpegPath = process.env.FFMPEG_PATH || path.join(path.dirname(require.resolve('@ffmpeg-installer/linux-x64/package.json')), 'ffmpeg');
const sha = bytes => createHash('sha256').update(bytes).digest('hex');

export async function runProcess(command, args, signal) {
  if (signal?.aborted) throw new Error('Cancelled');
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, { stdio: ['ignore', 'pipe', 'pipe'] });
    let stderr = '', stdout = ''; let settled = false;
    const abort = () => { child.kill('SIGTERM'); setTimeout(() => { if (!settled) child.kill('SIGKILL'); }, 1500).unref(); };
    signal?.addEventListener('abort', abort, { once:true });
    child.stderr.on('data', b => { stderr = (stderr + b).slice(-12000); });
    child.stdout.on('data', b => { stdout = (stdout + b).slice(-12000); });
    child.on('error', e => { settled = true; signal?.removeEventListener('abort', abort); reject(e); });
    child.on('close', code => { settled = true; signal?.removeEventListener('abort', abort); if (code === 0 && !signal?.aborted) resolve({stdout,stderr}); else reject(new Error(signal?.aborted ? 'Cancelled' : `Process exited ${code}: ${stderr}`)); });
  });
}

export async function renderVideo({ outputDir, config = {}, scene = 'scenes/demo.mjs', critic = null, audioFile = null, signal, onProgress = () => {} }) {
  const c = validateConfig(config);
  if (!outputDir || !path.isAbsolute(outputDir)) throw new Error('Absolute outputDir required');
  const scenePath = path.resolve(projectRoot, scene);
  if (!scenePath.startsWith(projectRoot + path.sep)) throw new Error('Scene must be inside the project');
  const source = await readFile(scenePath);
  await mkdir(path.join(outputDir, 'frames'), {recursive:true});
  const started = new Date().toISOString();
  const manifest = { version:1, started, config:c, scene, sceneSHA256:sha(source),
    renderer:'playwright-canvas', node:process.version, browser:null, status:'rendering',
    grading:'structural engineering checks; NOT perceptual/artistic quality', semanticProvider:critic ? 'supplied' : 'not-provided',
    audio:audioFile ? 'supplied' : 'none', frames:[], errors:[] };
  const manifestPath = path.join(outputDir,'manifest.json');
  let browser;
  const persist = () => writeFile(manifestPath, JSON.stringify(manifest,null,2)+'\n');
  try {
    browser = await chromium.launch({ headless:true, args:['--disable-gpu'] });
    manifest.browser = browser.version();
    const context = await browser.newContext({viewport:{width:c.width,height:c.height},deviceScaleFactor:1,locale:'en-US',timezoneId:'UTC'});
    // Resolve trusted local modules/assets only. No external network in rendered scenes.
    await context.route('**/*', async route => {
      try {
        const u = new URL(route.request().url());
        if (u.origin !== 'http://studio.internal') return await route.abort();
        if(u.pathname==='/__frame') return await route.fulfill({status:200,contentType:'text/html',body:`<html><body style="margin:0;background:#000"><canvas id="frame" width="${c.width}" height="${c.height}"></canvas></body></html>`});
        const rel = decodeURIComponent(u.pathname).replace(/^\/+/, '');
        const target = path.resolve(projectRoot,rel);
        if (!target.startsWith(projectRoot+path.sep) || !/^(scenes|assets|quality)\//.test(rel)) return await route.abort();
        const mime = {'.mjs':'text/javascript','.js':'text/javascript','.json':'application/json','.png':'image/png','.svg':'image/svg+xml','.jpg':'image/jpeg'}[path.extname(target)];
        if (!mime) return await route.abort();
        await route.fulfill({status:200,body:await readFile(target),contentType:mime,headers:{'Access-Control-Allow-Origin':'*'}});
      } catch { await route.abort(); }
    });
    await context.addInitScript(() => {
      const NativeDate=Date;
      window.__frameClock={time:0,seed:1};
      window.Date=class extends NativeDate {
        constructor(...args){super(...(args.length?args:[window.__frameClock.time*1000]));}
        static now(){return window.__frameClock.time*1000;}
      };
      Object.defineProperty(performance,'now',{value:()=>window.__frameClock.time*1000});
      Math.random=()=>{let x=window.__frameClock.seed|0;x^=x<<13;x^=x>>>17;x^=x<<5;window.__frameClock.seed=x;return (x>>>0)/4294967296;};
    });
    const page = await context.newPage();
    page.setDefaultTimeout(15000);
    await page.goto('http://studio.internal/__frame');
    await page.addScriptTag({type:'module', content:`import { render } from ${JSON.stringify('http://studio.internal/'+path.relative(projectRoot,scenePath).split(path.sep).join('/'))}; window.paint = render;`});
    await page.waitForFunction(() => typeof window.paint === 'function');
    let previous;
    for (let frame=0; frame<c.frameCount; frame++) {
      if (signal?.aborted) throw new Error('Cancelled');
      const record = {frame,time:frame/c.fps,attempts:[],accepted:false};
      let patch = null, acceptedSamples;
      for (let revision=0; revision<c.maxAttempts; revision++) {
        if (signal?.aborted) throw new Error('Cancelled');
        const payload = {frame,time:frame/c.fps,duration:c.duration,fps:c.fps,width:c.width,height:c.height,revision,beatMap:c.beatMap,patch};
        const captured = await page.evaluate(async payload => {
          window.__frameClock.time=payload.time; window.__frameClock.seed=(payload.frame+1)*2654435761;
          const canvas=document.getElementById('frame'), ctx=canvas.getContext('2d');
          ctx.reset(); ctx.clearRect(0,0,canvas.width,canvas.height);
          const note = await window.paint(ctx,payload) || {};
          await document.fonts.ready;
          if (document.getAnimations().length || document.body.children.length !== 1) throw new Error('Scene must use frame-painted Canvas, not CSS/DOM animations');
          return { png:canvas.toDataURL('image/png').split(',')[1], intentionalHold:note.intentionalHold === true };
        },payload);
        const bytes=Buffer.from(captured.png,'base64');
        const file=path.join(outputDir,'frames',String(frame).padStart(6,'0')+'.png');
        await writeFile(file,bytes);
        const structural=analyzePNG(bytes,previous,{...c,intentionalHold:captured.intentionalHold});
        const semantic=critic ? await critic.analyze({imagePath:file,frame,time:payload.time,beatMap:c.beatMap,metrics:structural.metrics,revision}) : null;
        const verdict=decideQuality(structural,semantic,c.threshold);
        record.attempts.push({revision,sha256:sha(bytes),...verdict,metrics:structural.metrics});
        onProgress({phase:'rendering',frame:frame+1,total:c.frameCount,revision,score:verdict.structuralScore,semanticReview:verdict.semanticReview});
        if (verdict.passed) { record.accepted=true; acceptedSamples=structural.samples; break; }
        patch=semantic?.patch ?? null;
      }
      manifest.frames.push(record);
      if (!record.accepted) { await persist(); throw new Error(`Frame ${frame} rejected after ${c.maxAttempts} bounded attempts`); }
      previous=acceptedSamples;
      if (frame % 12 === 0) await persist();
    }
    await browser.close(); browser=null;
    if (signal?.aborted) throw new Error('Cancelled');
    manifest.status='encoding'; await persist(); onProgress({phase:'encoding',frame:c.frameCount,total:c.frameCount});
    const videoPath=path.join(outputDir,'film.mp4');
    const args=['-hide_banner','-loglevel','error','-y','-framerate',String(c.fps),'-start_number','0','-i',path.join(outputDir,'frames','%06d.png')];
    if (audioFile) args.push('-i',path.resolve(audioFile),'-map','0:v:0','-map','1:a:0','-af','apad','-c:a','aac','-b:a','192k');
    args.push('-c:v','libx264','-threads','2','-pix_fmt','yuv420p','-crf','18','-movflags','+faststart','-t',String(c.duration),videoPath);
    await runProcess(ffmpegPath,args,signal);
    const info=await runProcess(ffmpegPath,['-version']);
    manifest.ffmpeg=info.stdout.split('\n')[0];
    manifest.videoSHA256=sha(await readFile(videoPath));
    manifest.status=critic ? 'provider-approved' : 'structural-pass'; manifest.finished=new Date().toISOString();
    manifest.iterations=manifest.frames.reduce((n,f)=>n+f.attempts.length,0);
    manifest.improvements=manifest.frames.filter(f=>f.attempts.length>1 && ((f.attempts.at(-1).semanticScore??f.attempts.at(-1).structuralScore) > (f.attempts[0].semanticScore??f.attempts[0].structuralScore))).length;
    await persist(); onProgress({phase:'complete',frame:c.frameCount,total:c.frameCount,status:manifest.status});
    return {manifest,videoPath,manifestPath};
  } catch (error) {
    manifest.status=signal?.aborted ? 'cancelled' : 'failed'; manifest.errors.push(error.message); manifest.finished=new Date().toISOString();
    await persist(); throw error;
  } finally { if (browser) await browser.close(); }
}
