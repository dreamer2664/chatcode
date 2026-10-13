import test from 'node:test';
import assert from 'node:assert/strict';
import {PNG} from 'pngjs';
import {validateConfig} from '../engine/config.mjs';
import {analyzePNG,decideQuality} from '../engine/quality.mjs';

function image(fn){const p=new PNG({width:160,height:90});for(let y=0;y<90;y++)for(let x=0;x<160;x++){const i=(y*160+x)*4;const rgb=fn(x,y);p.data[i]=rgb[0];p.data[i+1]=rgb[1];p.data[i+2]=rgb[2];p.data[i+3]=rgb[3]??255;}return PNG.sync.write(p);}
const conf={width:160,height:90};
test('default config and exact frame budget',()=>{const c=validateConfig();assert.equal(c.frameCount,96);assert.equal(c.duration,4);});
test('invalid config rejected',()=>{for(const input of [{width:161},{fps:Infinity},{fps:0},{duration:NaN},{duration:0},{duration:31},{duration:30,fps:60},{maxAttempts:5},{threshold:7},{width:'960'},{height:89},{duration:.01}])assert.throws(()=>validateConfig(input));});
test('beat map must be bounded and monotonic',()=>{for(const beats of [[1,.5],[-1],[0,0],[100],[NaN],'invalid'])assert.throws(()=>validateConfig({beatMap:{beats}}));assert.deepEqual(validateConfig({beatMap:{beats:[0,1,2]}}).beatMap,{beats:[0,1,2],cuts:[]});});
test('blank frame fails even if unrelated checks pass',()=>{const q=analyzePNG(image(()=>[240,240,240]),null,conf);assert.equal(decideQuality(q,null).passed,false);assert.ok(q.issues.includes('contrast'));});
test('detailed frame has meaningful structural evidence',()=>{const q=analyzePNG(image((x,y)=>[x%32*8,y%32*8,(x+y)%32*8]),null,conf);assert.equal(decideQuality(q,null).passed,true);assert.equal(q.score,10);assert.equal(decideQuality(q,null).semanticReview,'not-provided');});
test('repeated frame is dead unless explicitly held',()=>{const bytes=image((x,y)=>[x%32*8,y%32*8,(x+y)%32*8]);const first=analyzePNG(bytes,null,conf);const second=analyzePNG(bytes,first.samples,conf);assert.equal(decideQuality(second,null).passed,false);assert.equal(decideQuality(analyzePNG(bytes,first.samples,{...conf,intentionalHold:true}),null).passed,true);});
test('semantic critic cannot approve malformed/blank frames',()=>{const q=analyzePNG(image(()=>[240,240,240]),null,conf);assert.equal(decideQuality(q,{score:10,issues:[]}).passed,false);});
test('bad semantic scores refused',()=>{const q=analyzePNG(image((x,y)=>[x%32*8,y%32*8,(x+y)%32*8]),null,conf);for(const score of [NaN,Infinity,11,-1,'8'])assert.throws(()=>decideQuality(q,{score}));assert.equal(decideQuality(q,{score:7,issues:['off-beat']}).passed,false);});
test('wrong dimensions never pass',()=>{const q=analyzePNG(image((x,y)=>[x%32*8,y%32*8,(x+y)%32*8]),null,{width:320,height:180});assert.equal(decideQuality(q,null).passed,false);});
