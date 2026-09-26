const assert=require('assert');
const fs=require('fs');
const vm=require('vm');
const path=require('path');
const skill=require('../web/fsa-skill-analysis.js');

const fsaPath=path.resolve(process.cwd(),'fsa-source','telemetry-v1.js');
const source=fs.readFileSync(fsaPath,'utf8');

const rpcCalls=[];
const store=new Map([
  ['sb-nqcshihyfhthywpseilx-auth-token',JSON.stringify({access_token:'qa-token'})]
]);

const sandbox={
  console,
  crypto: require('crypto').webcrypto,
  navigator:{userAgent:'FSA-Android-v12',connection:{saveData:false,effectiveType:'4g'}},
  localStorage:{getItem:k=>store.get(k)??null,setItem:(k,v)=>store.set(k,String(v))},
  matchMedia:()=>({matches:false}),
  document:{
    hidden:false,visibilityState:'visible',
    getElementById:()=>null,
    addEventListener:()=>{}
  },
  addEventListener:()=>{},
  setInterval:()=>0,
  clearInterval:()=>{},
  Date,
  JSON,
  Math,
  globalThis:null,
  window:null,
  fetch:async(url,opts)=>{
    const name=String(url).split('/').pop();
    const body=JSON.parse(opts?.body||'{}');
    rpcCalls.push({name,body});
    if(name==='fsa_rpc_telemetry_start') return new Response(JSON.stringify('11111111-1111-4111-8111-111111111111'),{status:200});
    if(name==='fsa_rpc_telemetry_event') return new Response('1',{status:200});
    if(name==='fsa_rpc_telemetry_end') return new Response('',{status:204});
    return new Response('not found',{status:404});
  },
  Response
};
sandbox.window=sandbox;
sandbox.globalThis=sandbox;

vm.runInNewContext(source,sandbox,{filename:'telemetry-v1.js'});
const api=sandbox.__FSA_TELEMETRY_V1__;
assert.ok(api,'F.S.A. telemetry runtime handle must exist');

(async()=>{
  await api.record('shot_fired',{payload:{targetId:'fish-qa',cannonLevel:1}});
  await api.record('target_hit',{payload:{targetId:'fish-qa',damage:1}});
  await api.record('target_destroyed',{payload:{targetId:'fish-qa'}});
  await api.end();

  const eventCalls=rpcCalls.filter(x=>x.name==='fsa_rpc_telemetry_event');
  assert.strictEqual(eventCalls.length,3,'runtime should emit three telemetry event RPCs');
  assert.deepStrictEqual(eventCalls.map(x=>x.body.p_event_type),['shot_fired','target_hit','target_destroyed']);

  const base=Date.parse('2026-09-26T08:00:00Z');
  const events=eventCalls.map((x,i)=>({
    sourceProduct:'fsa',
    sessionId:x.body.p_session_id,
    eventType:x.body.p_event_type,
    occurredAt:new Date(base+i*1000).toISOString(),
    evidenceLabel:'exact_telemetry',
    confidence:1,
    payload:x.body.p_payload
  }));

  const out=skill.analyzeSkillSession({sessionId:eventCalls[0].body.p_session_id,events});
  assert.strictEqual(out.metrics.shots,1);
  assert.strictEqual(out.metrics.hits,1);
  assert.strictEqual(out.metrics.targetsDestroyed,1);
  assert.strictEqual(out.metrics.hitRate,1);
  assert.strictEqual(out.metrics.destroyRate,1);
  assert.strictEqual(out.metrics.meanHitLatencyMs,1000);
  assert.match(out.evidence.limitation,/does not predict/i);
  console.log('F.S.A. runtime telemetry -> EGM4000 analysis bridge: PASS');
})().catch(err=>{console.error(err);process.exit(1)});
