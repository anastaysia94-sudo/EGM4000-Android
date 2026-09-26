const assert=require('assert');
const fs=require('fs');
const skill=require('../web/fsa-skill-analysis.js');
const fixture=JSON.parse(fs.readFileSync('shared/fixtures/sample-fsa-exact-telemetry-session.json','utf8'));

const out=skill.analyzeSkillSession(fixture);
assert.strictEqual(out.schema,'egm4000.fsa-skill-analysis.v1');
assert.strictEqual(out.sourceProduct,'fsa');
assert.strictEqual(out.metrics.shots,1);
assert.strictEqual(out.metrics.hits,1);
assert.strictEqual(out.metrics.targetsDestroyed,1);
assert.strictEqual(out.metrics.hitRate,1);
assert.strictEqual(out.metrics.destroyRate,1);
assert.strictEqual(out.metrics.meanHitLatencyMs,2000);
assert.ok(out.evidence.limitation.includes('does not predict'));

const later=JSON.parse(JSON.stringify(fixture));
later.sessionId='fsa-demo-session-002';
later.events.push(
 {sourceProduct:'fsa',sessionId:'fsa-demo-session-002',eventId:'evt-010',eventType:'shot_fired',occurredAt:'2026-09-06T09:00:20Z',evidenceLabel:'exact_telemetry',confidence:1,payload:{targetId:'fish-2'}},
 {sourceProduct:'fsa',sessionId:'fsa-demo-session-002',eventId:'evt-011',eventType:'target_hit',occurredAt:'2026-09-06T09:00:21Z',evidenceLabel:'exact_telemetry',confidence:1,payload:{targetId:'fish-2'}}
);
const cmp=skill.compareSkillSessions(out,skill.analyzeSkillSession(later));
assert.strictEqual(cmp.schema,'egm4000.fsa-skill-comparison.v1');
assert.ok(cmp.caution.includes('not a prediction'));
console.log('EGM4000 F.S.A. skill-analysis smoke test passed');

const index=fs.readFileSync('web/index.html','utf8');
assert.ok(index.includes('fsa-skill-analysis.js'));
assert.ok(index.includes('id="analyzeFsa"'));
assert.ok(index.includes('EGMFsaSkillAnalysis.analyzeSkillSession'));
