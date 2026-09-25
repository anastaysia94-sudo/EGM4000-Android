(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  root.EGMFsaSkillAnalysis=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';

  const asType=e=>String(e?.eventType ?? e?.type ?? 'unknown');
  const asTime=e=>new Date(e?.occurredAt ?? e?.time ?? 0).getTime();
  const target=e=>e?.payload?.targetId ?? e?.targetId ?? null;

  function analyzeSkillSession(input){
    const events=Array.isArray(input)?input:(input?.events ?? []);
    const ordered=[...events].sort((a,b)=>asTime(a)-asTime(b));
    const shots=ordered.filter(e=>['shot_fired','shot'].includes(asType(e)));
    const hits=ordered.filter(e=>['target_hit','hit'].includes(asType(e)));
    const destroys=ordered.filter(e=>['target_destroyed','destroy'].includes(asType(e)));
    const hitRate=shots.length ? hits.length/shots.length : null;
    const destroyRate=hits.length ? destroys.length/hits.length : null;

    const shotByTarget=new Map();
    for(const e of shots){
      const id=target(e);
      if(id && !shotByTarget.has(id)) shotByTarget.set(id,asTime(e));
    }
    const hitLatencies=[];
    for(const e of hits){
      const id=target(e);
      const shotAt=id ? shotByTarget.get(id) : null;
      const hitAt=asTime(e);
      if(Number.isFinite(shotAt) && Number.isFinite(hitAt) && hitAt>=shotAt){
        hitLatencies.push(hitAt-shotAt);
      }
    }
    const meanHitLatencyMs=hitLatencies.length
      ? Math.round(hitLatencies.reduce((a,b)=>a+b,0)/hitLatencies.length)
      : null;

    const shotTimes=shots.map(asTime).filter(Number.isFinite);
    const gaps=[];
    for(let i=1;i<shotTimes.length;i++) gaps.push(shotTimes[i]-shotTimes[i-1]);
    const meanShotGapMs=gaps.length ? Math.round(gaps.reduce((a,b)=>a+b,0)/gaps.length) : null;

    const confidence=Math.min(1,(shots.length+hits.length+destroys.length)/20);
    const observations=[];
    if(hitRate!==null) observations.push({
      id:'hit_rate',
      label:'Recorded hit rate',
      value:Number(hitRate.toFixed(3)),
      plainLanguage:`${Math.round(hitRate*100)}% of recorded shots were followed by a recorded hit.`
    });
    if(meanHitLatencyMs!==null) observations.push({
      id:'hit_latency',
      label:'Mean shot-to-hit delay',
      value:meanHitLatencyMs,
      unit:'ms',
      plainLanguage:`Recorded hits arrived about ${meanHitLatencyMs} ms after the first recorded shot at that target.`
    });
    if(meanShotGapMs!==null) observations.push({
      id:'shot_gap',
      label:'Mean gap between shots',
      value:meanShotGapMs,
      unit:'ms',
      plainLanguage:`The average recorded time between shots was ${meanShotGapMs} ms.`
    });

    return {
      schema:'egm4000.fsa-skill-analysis.v1',
      sourceProduct:'fsa',
      sessionId:String(input?.sessionId ?? ordered[0]?.sessionId ?? 'unknown'),
      generatedAt:new Date().toISOString(),
      metrics:{
        shots:shots.length,
        hits:hits.length,
        targetsDestroyed:destroys.length,
        hitRate:hitRate===null?null:Number(hitRate.toFixed(3)),
        destroyRate:destroyRate===null?null:Number(destroyRate.toFixed(3)),
        meanHitLatencyMs,
        meanShotGapMs
      },
      evidence:{
        eventCount:ordered.length,
        confidence:Number(confidence.toFixed(3)),
        limitation:'Descriptive skill telemetry only. It does not predict random outcomes, hidden game state, prizes, or future results.'
      },
      observations
    };
  }

  function compareSkillSessions(before,after){
    const a=before?.metrics?before:analyzeSkillSession(before);
    const b=after?.metrics?after:analyzeSkillSession(after);
    const delta=(x,y)=>x==null||y==null?null:Number((y-x).toFixed(3));
    return {
      schema:'egm4000.fsa-skill-comparison.v1',
      beforeSessionId:a.sessionId,
      afterSessionId:b.sessionId,
      delta:{
        hitRate:delta(a.metrics.hitRate,b.metrics.hitRate),
        destroyRate:delta(a.metrics.destroyRate,b.metrics.destroyRate),
        meanHitLatencyMs:delta(a.metrics.meanHitLatencyMs,b.metrics.meanHitLatencyMs),
        meanShotGapMs:delta(a.metrics.meanShotGapMs,b.metrics.meanShotGapMs)
      },
      caution:'This comparison measures recorded player-control behavior in F.S.A. only; it is not a prediction or gambling strategy.'
    };
  }

  return {version:'1.0.0',analyzeSkillSession,compareSkillSessions};
});