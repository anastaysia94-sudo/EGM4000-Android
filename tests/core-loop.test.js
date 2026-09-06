const assert = require('assert');
const core = require('../web/egm-core-loop.js');

const t0 = Date.parse('2026-09-06T00:00:00Z');
const seq = [
  ['shot',0],['shot',0],['credit_up',10],['shot',0],['credit_down',-10],
  ['shot',0],['shot',0],['shot',0],['credit_down',-10],['shot',0],
  ['shot',0],['shot',0],['credit_down',-10],['shot',0],['credit_down',-10]
];
const events = seq.map((x,i)=>({
  sessionId:'baseline', platform:'F.S.A. Sandbox', type:x[0], creditDelta:x[1],
  source:'exact_telemetry', evidenceType:'exact_telemetry', confidence:1,
  time:new Date(t0+i*60000).toISOString()
}));

const out = core.run(events);
assert.strictEqual(out.analysis.schema,'egm.analysis.v1');
assert.strictEqual(out.analysis.metrics.eventCount,15);
assert.strictEqual(out.analysis.metrics.creditNet,-30);
assert.ok(out.analysis.evidence.confidence > 0.8);
assert.ok(out.analysis.patterns.some(p=>p.id==='negative_net'));
assert.ok(out.coaching.length >= 1);
assert.ok(out.coaching.every(c=>c.safety && c.evidenceLabel));

const after = events.map((e,i)=>({...e,sessionId:'after',time:new Date(t0+i*70000).toISOString()}));
after.push({sessionId:'after',platform:'F.S.A. Sandbox',type:'break',creditDelta:0,source:'exact_telemetry',evidenceType:'exact_telemetry',confidence:1,time:new Date(t0+16*70000).toISOString()});
const cmp = core.compareSessions(out.analysis,core.analyzeSession(after),out.coaching[0]);
assert.strictEqual(cmp.schema,'egm.comparison.v1');
assert.ok(['improved','worsened','unchanged','insufficient_evidence'].includes(cmp.evaluation));
assert.ok(cmp.caution.includes('cannot establish hidden game mechanics'));

console.log('EGM4000 core-loop smoke test passed');
