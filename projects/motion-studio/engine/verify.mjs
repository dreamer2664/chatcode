import {readFile,readdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateConfig} from './config.mjs';
import {analyzePNG,decideQuality} from './quality.mjs';
import {runProcess,ffmpegPath} from './render.mjs';

const sha=b=>createHash('sha256').update(b).digest('hex');
const hashPattern=/^[a-f0-9]{64}$/;
const demand=(condition,message)=>{if(!condition)throw new Error(message);};
const score=v=>Number.isFinite(v)&&v>=0&&v<=10;

/** Self-consistency and byte/pixel verification; NOT provenance signatures or taste review. */
export async function verifyRender(directory,{decode=false,sourceRoot=null,requireSemantic=false}={}) {
  const root=path.resolve(directory);const output={verdict:'FAIL',directory:root,checks:{},reasons:[]};
  try{
    const m=JSON.parse(await readFile(path.join(root,'manifest.json'),'utf8'));
    const c=validateConfig(m.config);
    demand(m.version===1,'Unsupported manifest version');
    demand(m.config.frameCount===c.frameCount,'Incorrect frame budget');
    demand(['structural-pass','provider-approved'].includes(m.status),'Run is not complete/approved');
    demand(Number.isFinite(Date.parse(m.started))&&Number.isFinite(Date.parse(m.finished))&&Date.parse(m.finished)>=Date.parse(m.started),'Invalid completion timestamps');
    const semantic=m.semanticProvider!=='not-provided';
    demand(m.semanticProvider==='not-provided'||m.semanticProvider==='supplied','Unknown semantic-provider evidence');
    demand(m.status===(semantic?'provider-approved':'structural-pass'),'Status contradicts semantic-provider evidence');
    demand(!requireSemantic||semantic,'Semantic provider required but not supplied');
    demand(Array.isArray(m.errors)&&m.errors.length===0,'Completed run carries errors');
    demand(Array.isArray(m.frames)&&m.frames.length===c.frameCount,'Missing/extra frame records');
    const files=(await readdir(path.join(root,'frames'))).filter(f=>f.endsWith('.png')).sort();
    const expected=Array.from({length:c.frameCount},(_,i)=>String(i).padStart(6,'0')+'.png');
    demand(JSON.stringify(files)===JSON.stringify(expected),'Missing/extra frame PNGs');
    let previous,attempts=0,improved=0;
    for(let i=0;i<c.frameCount;i++){
      const f=m.frames[i];demand(f.frame===i,'Out-of-order or duplicate frame record');
      demand(Number.isFinite(f.time)&&Math.abs(f.time-i/c.fps)<1e-9,'Frame timestamp is not frame/fps');
      demand(f.accepted===true&&Array.isArray(f.attempts)&&f.attempts.length>=1&&f.attempts.length<=c.maxAttempts,'Invalid acceptance/attempt budget');
      f.attempts.forEach((a,j)=>{
        demand(a.revision===j,'Attempt revision sequence is wrong');
        demand(hashPattern.test(a.sha256),'Malformed PNG hash');
        demand(score(a.structuralScore),'Invalid structural score');
        demand(semantic?score(a.semanticScore):a.semanticScore===null,'Semantic score contradicts provider');
        demand(typeof a.passed==='boolean'&&Array.isArray(a.issues),'Invalid attempt verdict');
        demand(j===f.attempts.length-1 ? a.passed : !a.passed,'Attempts continue after a passing verdict');
      });
      const a=f.attempts.at(-1);let acceptedSamples;
      for(let revision=0;revision<f.attempts.length;revision++){
        const attempt=f.attempts[revision],last=revision===f.attempts.length-1;
        const expectedArtifact=last ? `frames/${expected[i]}` : `attempts/${String(i).padStart(6,'0')}-r${revision}.png`;
        // M1 legacy single-pass records have no artifact field; rejected history must be retained.
        demand(last ? (!attempt.artifact||attempt.artifact===expectedArtifact) : attempt.artifact===expectedArtifact,'Missing/unsafe attempt artifact');
        demand(attempt.intentionalHold===undefined||typeof attempt.intentionalHold==='boolean','Invalid intentional-hold declaration');
        const bytes=await readFile(path.join(root,expectedArtifact));
        demand(sha(bytes)===attempt.sha256,'Frame PNG hash mismatch: '+i+' revision '+revision);
        const actual=analyzePNG(bytes,previous,{...c,intentionalHold:attempt.intentionalHold===true});
        demand(actual.score===attempt.structuralScore,'Recorded structural score disagrees with pixels: '+i);
        const verdict=decideQuality(actual,semantic?{score:attempt.semanticScore,issues:[]}:null,c.threshold);
        demand(verdict.passed===attempt.passed,'Recomputed quality gate contradicts attempt: '+i);
        demand(attempt.semanticReview===verdict.semanticReview,'Semantic-review label contradicts score: '+i);
        for(const [key,value] of Object.entries(actual.metrics)){
          const recorded=attempt.metrics?.[key];
          demand(value===null?recorded===null:Number.isFinite(recorded)&&Math.abs(recorded-value)<1e-6,'Recorded metric disagrees with pixels: '+i+' '+key);
        }
        if(last)acceptedSamples=actual.samples;
      }
      previous=acceptedSamples;attempts+=f.attempts.length;
      if(f.attempts.length>1&&(a.semanticScore??a.structuralScore)>(f.attempts[0].semanticScore??f.attempts[0].structuralScore))improved++;
    }
    demand(m.iterations===attempts&&m.improvements===improved,'Iteration/improvement summary mismatch');
    output.checks.frames={count:c.frameCount,hashes:'match',pixelMetrics:'recomputed',timing:'explicit frame/fps',attempts,improvements:improved};
    demand(hashPattern.test(m.videoSHA256),'Malformed video hash');
    const movie=path.join(root,'film.mp4');demand(sha(await readFile(movie))===m.videoSHA256,'MP4 hash mismatch');
    output.checks.videoHash='match';
    demand(typeof m.scene==='string'&&hashPattern.test(m.sceneSHA256),'Missing/malformed scene fingerprint');
    if(m.moduleHashes&&Object.keys(m.moduleHashes).length) demand(m.moduleHashes[m.scene]===m.sceneSHA256,'Loaded scene does not match declared scene hash');
    if(sourceRoot){
      const base=path.resolve(sourceRoot);
      const fingerprints={...(m.engineHashes??{}),...(m.moduleHashes??{})};
      if(!Object.keys(fingerprints).length){
        demand(typeof m.scene==='string','Missing scene path');fingerprints[m.scene]=m.sceneSHA256;
        output.checks.sourceCoverage='legacy scene-only; imports/engine not fingerprinted';
      }else output.checks.sourceCoverage='recorded engine + loaded modules/assets (not fonts/system libraries)';
      for(const [rel,digest] of Object.entries(fingerprints)){
        const target=path.resolve(base,rel);
        demand(target.startsWith(base+path.sep)&&hashPattern.test(digest),'Unsafe/malformed source fingerprint');
        demand(sha(await readFile(target))===digest,'Source drift: '+rel);
      }
      output.checks.sourceHashes={count:Object.keys(fingerprints).length,result:'match'};
    }else output.checks.sourceHashes='not requested';
    if(decode){
      const result=await runProcess(ffmpegPath,['-hide_banner','-i',movie,'-map','0:v:0','-vsync','0','-progress','pipe:1','-f','null','-']);
      const frames=[...result.stdout.matchAll(/^frame=(\d+)$/gm)].map(m=>Number(m[1]));
      demand(frames.at(-1)===c.frameCount,'Decoded video frame count mismatch');
      const times=[...result.stdout.matchAll(/^out_time=(\d+):(\d+):([\d.]+)$/gm)].map(v=>3600*Number(v[1])+60*Number(v[2])+Number(v[3]));
      demand(Number.isFinite(times.at(-1))&&Math.abs(times.at(-1)-c.duration)<.002,'Decoded duration mismatch');
      const stream=result.stderr.split('\n').find(line=>/Stream #0:\d+.*Video:/.test(line));
      const dimensions=stream?.match(/\b(\d{2,5})x(\d{2,5})\b/);
      demand(dimensions&&Number(dimensions[1])===c.width&&Number(dimensions[2])===c.height,'Decoded dimensions mismatch');
      output.checks.decode={frames:frames.at(-1),duration:times.at(-1),dimensions:`${c.width}x${c.height}`};
    }else output.checks.decode='not requested';
    output.verdict='PASS';output.semanticReview=semantic?'provider score verified for consistency only':'not-provided';
    output.note='Byte/pixel self-consistency is NOT proof of authenticity, artistic quality, spring physics or beat sync. An attacker able to replace all files and fingerprints can forge a self-consistent bundle.';
  }catch(e){output.reasons.push(e.message);}
  return output;
}

if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const args=process.argv.slice(2),dir=args.shift();
  if(!dir){console.error('Usage: node engine/verify.mjs RENDER_DIR [--decode] [--require-semantic] [--source-root PATH]');process.exitCode=2;}
  else{
    let sourceRoot=null,decode=false,requireSemantic=false,error=null;
    for(let i=0;i<args.length;i++){
      if(args[i]==='--decode')decode=true;
      else if(args[i]==='--require-semantic')requireSemantic=true;
      else if(args[i]==='--source-root'&&args[i+1])sourceRoot=args[++i];
      else{error='Unknown/missing argument '+args[i];break;}
    }
    if(error){console.error(error);process.exitCode=2;}
    else{const result=await verifyRender(dir,{decode,sourceRoot,requireSemantic});console.log(JSON.stringify(result,null,2));process.exitCode=result.verdict==='PASS'?0:1;}
  }
}
