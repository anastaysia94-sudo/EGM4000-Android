(function(root,factory){
  const api=factory();
  if(typeof module==='object'&&module.exports) module.exports=api;
  root.EGMCoreLoop=api;
})(typeof globalThis!=='undefined'?globalThis:this,function(){
  'use strict';

  const EVIDENCE_WEIGHT={
    exact_telemetry:1,
    observed_evidence:0.88,
    estimate:0.62,
    correlation:0.5,
    hypothesis:0.35,
    unknown:0.2
  };

  const clamp=(n,min=0,max=1)=>Math.max(min,Math.min(max,Number(n)||0));
  const avg=xs=>xs.length?xs.reduce((a,b)=>a+b,0)/xs.length:0;
  const iso=t=>{const d=new Date(t||Date.now());return Number.isNaN(d.getTime())?new Date().toISOString():d.toISOString()};

  function normalizeEvent(raw={},ctx={}){
    const creditDelta=Number(raw.creditDelta ?? raw.payload?.creditDelta ?? 0) || 0;
    const evidenceType=raw.evidenceType || (raw.provenance==='exact_telemetry'?'exact_telemetry':'observed_evidence');
    return {
      schema:'egm.event.v1',
      sessionId:String(raw.sessionId ?? ctx.sessionId ?? 'local-session'),
      sourceEventId:raw.sourceEventId ?? raw.id ?? null,
      platform:String(raw.platform ?? ctx.platform ?? 'Unknown'),
      type:String(raw.type ?? 'unknown'),
      time:iso(raw.time),
      source:String(raw.source ?? raw.provenance ?? ctx.source ?? 'user_recorded'),
      evidenceType:EVIDENCE_WEIGHT[evidenceType]!==undefined?evidenceType:'unknown',
      confidence:clamp(raw.confidence ?? 1),
      payload:{
        ...(raw.payload||{}),
        creditDelta,
        note:String(raw.note ?? raw.payload?.note ?? '')
      }
    };
  }

  function eventReliability(e){
    return clamp((EVIDENCE_WEIGHT[e.evidenceType] ?? 0.2) * clamp(e.confidence));
  }

  function analyzeSession(rawEvents=[],opts={}){
    const events=rawEvents.map(e=>normalizeEvent(e,opts)).sort((a,b)=>new Date(a.time)-new Date(b.time));
    const count=events.length;
    const times=events.map(e=>new Date(e.time).getTime()).filter(Number.isFinite);
    const durationMs=times.length>1?Math.max(0,times[times.length-1]-times[0]):0;
    const durationMinutes=durationMs/60000;
    const shots=events.filter(e=>e.type==='shot').length;
    const breaks=events.filter(e=>e.type==='break').length;
    const deltas=events.map(e=>Number(e.payload.creditDelta)||0);
    const creditNet=deltas.reduce((a,b)=>a+b,0);
    const positiveCreditEvents=deltas.filter(x=>x>0).length;
    const negativeCreditEvents=deltas.filter(x=>x<0).length;
    const creditVolatility=avg(deltas.map(Math.abs));
    const shotsPerMinute=durationMinutes>0?shots/durationMinutes:shots;

    let cumulative=0,peak=0,maxDrawdown=0;
    for(const d of deltas){
      cumulative+=d;
      peak=Math.max(peak,cumulative);
      maxDrawdown=Math.max(maxDrawdown,peak-cumulative);
    }

    const half=Math.max(1,Math.floor(count/2));
    const first=events.slice(0,half),second=events.slice(half);
    const shotCount=a=>a.filter(e=>e.type==='shot').length;
    const net=a=>a.reduce((n,e)=>n+(Number(e.payload.creditDelta)||0),0);
    const firstShots=shotCount(first),secondShots=shotCount(second);
    const firstNet=net(first),secondNet=net(second);

    const reliability=avg(events.map(eventReliability));
    const sampleFactor=clamp(count/20);
    const timeFactor=durationMinutes>=1?1:0.7;
    const confidence=clamp(reliability*(0.55+0.35*sampleFactor+0.10*timeFactor));
    const completeness=clamp((count?0.35:0) + (shots?0.2:0) + ((positiveCreditEvents+negativeCreditEvents)?0.25:0) + (durationMinutes>0?0.2:0));

    const patterns=[];
    const addPattern=(id,label,severity,evidence,patternConfidence,why)=>patterns.push({id,label,severity,evidence,confidence:clamp(patternConfidence),why});

    if(count>=3 && creditNet<0){
      addPattern('negative_net','Recorded credits finished below the session start','review',`Net credit movement ${creditNet}`,confidence,'This describes recorded session history only; it does not predict the next outcome.');
    }
    if(count>=8 && secondShots>firstShots*1.35 && secondNet<0){
      addPattern('pace_up_results_down','Shot pace increased while recorded credit movement weakened','warning',`First half: ${firstShots} shots / ${firstNet} credits; second half: ${secondShots} shots / ${secondNet} credits`,confidence*0.92,'A rising action rate alongside worse recorded results is a useful self-regulation signal, not evidence of hidden game state.');
    }
    if(maxDrawdown>0 && maxDrawdown>=Math.max(20,Math.abs(creditNet)*0.75)){
      addPattern('drawdown','Meaningful recorded drawdown occurred','warning',`Maximum observed drawdown ${maxDrawdown} credits`,confidence*0.9,'Large drawdowns in your own session history can justify a break or stop review.');
    }
    if(durationMinutes>=20 && breaks===0){
      addPattern('no_break_long_session','Long recorded session without a break','review',`${durationMinutes.toFixed(1)} minutes, 0 breaks`,confidence*0.82,'Break prompts are behavioral guardrails and do not imply future winnings or losses.');
    }
    if(count>=12 && creditNet>=0 && secondNet>=firstNet && secondShots<=Math.max(firstShots*1.2,firstShots+2)){
      addPattern('steady_pace','Stable pace accompanied non-worsening recorded results','info',`First half: ${firstShots} shots / ${firstNet}; second half: ${secondShots} shots / ${secondNet}`,confidence*0.75,'This is a descriptive correlation from this session, not a strategy guarantee.');
    }

    return {
      schema:'egm.analysis.v1',
      sessionId:events[0]?.sessionId || String(opts.sessionId||'local-session'),
      platform:events[0]?.platform || String(opts.platform||'Unknown'),
      generatedAt:new Date().toISOString(),
      evidence:{eventCount:count,evidenceTypes:[...new Set(events.map(e=>e.evidenceType))],meanReliability:Number(reliability.toFixed(3)),completeness:Number(completeness.toFixed(3)),confidence:Number(confidence.toFixed(3))},
      metrics:{eventCount:count,shots,breaks,creditNet,positiveCreditEvents,negativeCreditEvents,durationMinutes:Number(durationMinutes.toFixed(2)),shotsPerMinute:Number(shotsPerMinute.toFixed(2)),creditVolatility:Number(creditVolatility.toFixed(2)),maxDrawdown:Number(maxDrawdown.toFixed(2))},
      segments:{firstHalf:{shots:firstShots,creditNet:firstNet},secondHalf:{shots:secondShots,creditNet:secondNet}},
      patterns,
      normalizedEvents:events
    };
  }

  function buildCoaching(analysis){
    if(!analysis || !analysis.metrics) return [];
    const c=analysis.evidence?.confidence ?? 0;
    if(!analysis.metrics.eventCount) return [{id:'collect_evidence',priority:1,title:'Collect a consistent session sample',action:'Record shots, credit changes, breaks and timestamps before drawing conclusions.',evidence:'No session events recorded',confidence:1,evidenceLabel:'observed_evidence',measurement:{metric:'eventCount',direction:'increase'},safety:'No outcome prediction is being made.'}];

    const tips=[];
    const has=id=>analysis.patterns.some(p=>p.id===id);
    if(has('pace_up_results_down')) tips.push({id:'pace_guard',priority:1,title:'Use a pace guardrail',action:'For the next recorded session, keep shot pace at or below the first-half pace from this session and compare the result afterward.',evidence:analysis.patterns.find(p=>p.id==='pace_up_results_down').evidence,confidence:Number((c*0.92).toFixed(3)),evidenceLabel:'correlation',measurement:{metric:'shotsPerMinute',direction:'not_increase'},safety:'This tests your behavior; it does not predict game outcomes.'});
    if(has('drawdown')||has('negative_net')) tips.push({id:'drawdown_break',priority:2,title:'Add a drawdown stop-and-review trigger',action:'When your recorded drawdown reaches the same threshold again, pause and review before continuing.',evidence:`Observed max drawdown ${analysis.metrics.maxDrawdown}; net ${analysis.metrics.creditNet}`,confidence:Number((c*0.9).toFixed(3)),evidenceLabel:'observed_evidence',measurement:{metric:'maxDrawdown',direction:'decrease'},safety:'A stop trigger limits exposure; it does not increase the probability of winning.'});
    if(has('no_break_long_session')) tips.push({id:'scheduled_break',priority:3,title:'Schedule a break',action:'Add at least one explicit break in the next comparable session and compare pace, duration and drawdown afterward.',evidence:`${analysis.metrics.durationMinutes} minutes with ${analysis.metrics.breaks} breaks`,confidence:Number((c*0.82).toFixed(3)),evidenceLabel:'observed_evidence',measurement:{metric:'breaks',direction:'increase'},safety:'This is a behavioral wellness guardrail.'});
    if(!tips.length) tips.push({id:'repeat_baseline',priority:4,title:'Repeat the baseline before changing strategy',action:'Record another comparable session using the same event definitions, then compare pace, drawdown and net movement.',evidence:`${analysis.metrics.eventCount} events; analysis confidence ${c}`,confidence:Number((c*0.75).toFixed(3)),evidenceLabel:'observed_evidence',measurement:{metric:'evidence.completeness',direction:'increase'},safety:'More evidence reduces overinterpretation of one session.'});
    return tips.sort((a,b)=>a.priority-b.priority);
  }

  function compareSessions(before,after,coach=null){
    const a=before?.metrics?before:analyzeSession(before||[]);
    const b=after?.metrics?after:analyzeSession(after||[]);
    const delta={
      shotsPerMinute:Number((b.metrics.shotsPerMinute-a.metrics.shotsPerMinute).toFixed(2)),
      creditNet:Number((b.metrics.creditNet-a.metrics.creditNet).toFixed(2)),
      maxDrawdown:Number((b.metrics.maxDrawdown-a.metrics.maxDrawdown).toFixed(2)),
      breaks:b.metrics.breaks-a.metrics.breaks,
      evidenceCompleteness:Number(((b.evidence?.completeness||0)-(a.evidence?.completeness||0)).toFixed(3))
    };
    let evaluation='insufficient_evidence';
    if(coach?.measurement){
      const m=coach.measurement.metric;
      const key=m==='evidence.completeness'?'evidenceCompleteness':m;
      const d=delta[key];
      if(typeof d==='number'){
        if(coach.measurement.direction==='decrease') evaluation=d<0?'improved':d>0?'worsened':'unchanged';
        else if(coach.measurement.direction==='increase') evaluation=d>0?'improved':d<0?'worsened':'unchanged';
        else if(coach.measurement.direction==='not_increase') evaluation=d<=0?'improved':'worsened';
      }
    }
    return {schema:'egm.comparison.v1',generatedAt:new Date().toISOString(),beforeSessionId:a.sessionId,afterSessionId:b.sessionId,delta,evaluation,coachId:coach?.id||null,caution:'Comparison describes recorded sessions and cannot establish hidden game mechanics or guarantee future outcomes.'};
  }

  function run(rawEvents=[],opts={}){
    const analysis=analyzeSession(rawEvents,opts);
    return {analysis,coaching:buildCoaching(analysis)};
  }

  return {version:'1.0.0',normalizeEvent,analyzeSession,buildCoaching,compareSessions,run};
});
