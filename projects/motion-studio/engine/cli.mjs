import path from 'node:path';
import { pathToFileURL } from 'node:url';
import { renderVideo } from './render.mjs';

const args=process.argv.slice(2), opts={};
for(let i=0;i<args.length;i+=2){if(!args[i].startsWith('--') || !args[i+1]) throw new Error('Use --key value');opts[args[i].slice(2)]=args[i+1];}
const allowed=new Set(['out','fps','duration','width','height','attempts','scene','critic','audio']);
for(const k of Object.keys(opts)) if(!allowed.has(k)) throw new Error('Unknown option '+k);
const config={};for(const k of ['fps','duration','width','height']) if(opts[k])config[k]=Number(opts[k]);
if(opts.attempts)config.maxAttempts=Number(opts.attempts);
const critic=opts.critic ? await import(pathToFileURL(path.resolve(opts.critic)).href) : null;
const controller=new AbortController();for(const s of ['SIGTERM','SIGINT'])process.once(s,()=>controller.abort());
try {
 const result=await renderVideo({outputDir:path.resolve(opts.out||'renders/cli-demo'),config,scene:opts.scene||'scenes/demo.mjs',critic,audioFile:opts.audio,signal:controller.signal,onProgress:p=>{if(p.frame%12===0||p.phase!=='rendering')console.log(JSON.stringify(p));}});
 console.log(JSON.stringify({status:result.manifest.status,frames:result.manifest.frames.length,video:result.videoPath,semanticProvider:result.manifest.semanticProvider}));
}catch(e){console.error(e.message);process.exitCode=1;}
