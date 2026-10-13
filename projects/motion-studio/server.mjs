import http from 'node:http';
import { randomUUID } from 'node:crypto';
import { readFile, stat, readdir } from 'node:fs/promises';
import { createReadStream } from 'node:fs';
import path from 'node:path';
import { renderVideo, projectRoot } from './engine/render.mjs';
import { validateConfig } from './engine/config.mjs';

const jobs=new Map();let active=null;
const root=path.join(projectRoot,'renders');
const json=(res,code,payload)=>{res.writeHead(code,{'Content-Type':'application/json','Cache-Control':'no-store'});res.end(JSON.stringify(payload));};
const publicJob=j=>({...j,controller:undefined});
async function body(req){let s='';for await(const chunk of req){s+=chunk;if(s.length>8192)throw new Error('Request too large');}return JSON.parse(s||'{}');}
async function file(req,res,target,type){
 const info=await stat(target); let start=0,end=info.size-1,status=200;
 const range=req.headers.range;
 if(range){const m=/^bytes=(\d+)-(\d*)$/.exec(range);if(!m||Number(m[1])>=info.size){res.writeHead(416,{'Content-Range':`bytes */${info.size}`});return res.end();}start=Number(m[1]);end=m[2]?Math.min(Number(m[2]),end):end;if(end<start){res.writeHead(416);return res.end();}status=206;}
 const headers={'Content-Type':type,'Content-Length':end-start+1,'Accept-Ranges':'bytes','Cache-Control':'no-cache'};
 if(status===206)headers['Content-Range']=`bytes ${start}-${end}/${info.size}`;
 res.writeHead(status,headers);const stream=createReadStream(target,{start,end});stream.on('error',()=>res.destroy());stream.pipe(res);
}
const server=http.createServer(async(req,res)=>{
 try {
 const url=new URL(req.url,'http://studio.internal'),p=url.pathname;
 if(req.method==='GET'&&p==='/api/jobs')return json(res,200,{jobs:[...jobs.values()].map(publicJob).reverse(),active});
 if(req.method==='POST'&&p==='/api/jobs'){
  if(active)return json(res,409,{error:'Another render is running. One job at a time.'});
  const input=await body(req);
  const allowed=new Set(['width','height','fps','duration']);if(Object.keys(input).some(k=>!allowed.has(k)))return json(res,400,{error:'Only width, height, fps and duration may be set over HTTP.'});
  const config=validateConfig(input),id=randomUUID(),controller=new AbortController();
  const job={id,status:'queued',progress:{frame:0,total:config.frameCount},config,created:new Date().toISOString(),controller};
  jobs.set(id,job);active=id;json(res,202,publicJob(job));
  renderVideo({outputDir:path.join(root,id),config,signal:controller.signal,onProgress:p=>{job.progress=p;job.status=p.phase;}})
  .then(({manifest})=>{job.status='complete';job.verdict=manifest.status;job.semanticReview=manifest.semanticProvider;job.video=`/renders/${id}/film.mp4`;job.manifest=`/renders/${id}/manifest.json`;})
  .catch(e=>{job.status=controller.signal.aborted?'cancelled':'failed';job.error=e.message;job.manifest=`/renders/${id}/manifest.json`;})
  .finally(()=>{active=null;job.finished=new Date().toISOString();});return;
 }
 const match=/^\/api\/jobs\/([a-f0-9-]{36})\/cancel$/.exec(p);
 if(req.method==='POST'&&match){const j=jobs.get(match[1]);if(!j)return json(res,404,{error:'Unknown job'});j.controller.abort();return json(res,200,{cancelRequested:true});}
 const render=/^\/renders\/([a-zA-Z0-9_-]+)\/(film\.mp4|manifest\.json|frames\/[0-9]{6}\.png|attempts\/[0-9]{6}-r[0-9]\.png)$/.exec(p);
 if(req.method==='GET'&&render)return await file(req,res,path.join(root,render[1],render[2]),render[2].endsWith('.mp4')?'video/mp4':render[2].endsWith('.png')?'image/png':'application/json');
 const assets={'/':['ui/index.html','text/html'],'/app.js':['ui/app.js','text/javascript'],'/style.css':['ui/style.css','text/css'],'/scenes/demo.mjs':['scenes/demo.mjs','text/javascript']};
 if(req.method==='GET'&&assets[p]){const [f,type]=assets[p];return await file(req,res,path.join(projectRoot,f),type);}
 return json(res,404,{error:'Not found'});
 }catch(e){if(!res.headersSent)json(res,e.code==='ENOENT'?404:400,{error:e.code==='ENOENT'?'File not found':e.message});else res.destroy();}
});
// Recover completed evidence on restart; only safe local render directory names.
try {
  for (const name of await readdir(root)) {
    if (!/^[a-zA-Z0-9_-]+$/.test(name)) continue;
    try {
      const m=JSON.parse(await readFile(path.join(root,name,'manifest.json'),'utf8'));
      const complete=['structural-pass','provider-approved'].includes(m.status);
      jobs.set(name,{id:name,status:complete?'complete':m.status==='failed'?'failed':'cancelled',config:m.config,created:m.started,finished:m.finished,
        progress:{frame:m.frames.length,total:m.config.frameCount},verdict:m.status,semanticReview:m.semanticProvider,
        error:m.errors?.at(-1),video:complete?`/renders/${name}/film.mp4`:undefined,manifest:`/renders/${name}/manifest.json`,controller:new AbortController()});
    } catch { /* incomplete/malformed directory is not promoted to a completed job */ }
  }
} catch (e) { if(e.code!=='ENOENT') throw e; }
const port=Number(process.env.PORT||8787);
server.listen(port,'0.0.0.0',()=>console.log(`Motion Studio listening on 0.0.0.0:${port}`));
for(const s of ['SIGTERM','SIGINT'])process.once(s,()=>{for(const j of jobs.values())j.controller.abort();server.close(()=>process.exit());});
