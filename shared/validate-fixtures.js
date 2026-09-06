#!/usr/bin/env node
const fs=require('fs');
const path=require('path');
const root=__dirname;
const file=path.join(root,'fixtures','sample-fsa-exact-telemetry-session.json');
const doc=JSON.parse(fs.readFileSync(file,'utf8'));
function assert(v,msg){if(!v)throw new Error(msg)}
assert(doc.schema==='egm4000.fsa-session.v1','wrong session schema');
assert(doc.sourceProduct==='fsa','fixture must come from owned FSA');
assert(Number.isInteger(doc.userId)&&doc.userId>0,'userId required');
assert(typeof doc.sessionId==='string'&&doc.sessionId.length>0,'sessionId required');
assert(Array.isArray(doc.events)&&doc.events.length>=5,'events required');
const required=new Set(['session_started','round_started','shot_fired','target_hit','credit_changed','round_ended','session_ended']);
const ids=new Set();let last=0;
for(const e of doc.events){
  for(const k of ['sourceProduct','sessionId','eventId','eventType','occurredAt','evidenceLabel','confidence','payload']) assert(Object.prototype.hasOwnProperty.call(e,k),`missing ${k}`);
  assert(e.sourceProduct==='fsa','non-FSA source');
  assert(e.sessionId===doc.sessionId,'session mismatch');
  assert(e.evidenceLabel==='exact_telemetry','FSA fixture must be exact telemetry');
  assert(e.confidence===1,'exact FSA confidence must be 1');
  assert(!ids.has(e.eventId),'duplicate eventId');ids.add(e.eventId);
  const t=Date.parse(e.occurredAt);assert(Number.isFinite(t),'invalid occurredAt');assert(t>=last,'timestamps must be monotonic');last=t;
  required.delete(e.eventType);
  if(e.eventType==='credit_changed') assert(e.payload.currencyType==='virtual_non_cash_credit','FSA credits must be virtual/non-cash');
}
assert(required.size===0,'missing required event types: '+[...required].join(','));
const normalized=doc.events.map(e=>({schema:'egm.event.v1',sessionId:doc.sessionId,sourceEventId:e.eventId,platform:'fsa',type:e.eventType==='credit_changed'?'credit_change':e.eventType,time:e.occurredAt,source:'fsa-owned-bridge',evidenceType:'exact_telemetry',confidence:1,payload:e.payload}));
assert(normalized.every(e=>e.evidenceType==='exact_telemetry'&&e.source==='fsa-owned-bridge'),'normalization failed');
console.log(`FSA fixture valid: ${normalized.length} exact telemetry events`);
