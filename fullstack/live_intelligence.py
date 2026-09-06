from __future__ import annotations
import json
from datetime import datetime,timezone
from storage import rowdict,rowsdict

SCHEMA='egm.event.v1'
ANALYSIS_SCHEMA='egm.analysis.v1'
EXPERIMENT_SCHEMA='egm.coaching-experiment.v1'
EVIDENCE=('exact_telemetry','observed_evidence','estimate','correlation','hypothesis','unknown')
ADAPTERS=(
 {'id':'fire-kirin','name':'Fire Kirin','mode':'observed'},
 {'id':'panda-master','name':'Panda Master','mode':'observed'},
 {'id':'orion-stars','name':'Orion Stars','mode':'observed'},
 {'id':'juwa','name':'Juwa','mode':'observed'},
 {'id':'game-master','name':'Game Master / GameVault','mode':'observed'},
 {'id':'generic','name':'Generic Fish Shooter','mode':'observed'},
 {'id':'fsa','name':'F.S.A. Perfect Telemetry','mode':'exact'},
)

# C014 deliberately evaluates behavior/evidence-quality metrics only. Random credit
# outcomes remain descriptive evidence and are never treated as proof coaching worked.
EXPERIMENT_METRICS={
 'shots_per_min':{'direction':'lower_better','label':'shot pace'},
 'max_drawdown':{'direction':'lower_better','label':'recorded drawdown'},
 'breaks':{'direction':'higher_better','label':'recorded breaks'},
 'evidence_completeness':{'direction':'higher_better','label':'evidence completeness'},
}

def now_iso():return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def _exec_migration(con,sql):
    try:con.execute(sql);con.commit()
    except Exception:con.rollback()
def migrate(con):
    for sql in (
      'ALTER TABLE tips ADD COLUMN live_session_id INTEGER',
      "ALTER TABLE tips ADD COLUMN evidence_type TEXT NOT NULL DEFAULT 'observed_evidence'",
      'ALTER TABLE tips ADD COLUMN sample_size INTEGER NOT NULL DEFAULT 0',
      "ALTER TABLE tips ADD COLUMN uncertainty TEXT NOT NULL DEFAULT ''",
    ):_exec_migration(con,sql)
    idcol='SERIAL PRIMARY KEY' if con.postgres else 'INTEGER PRIMARY KEY AUTOINCREMENT'
    _exec_migration(con,f'''CREATE TABLE IF NOT EXISTS coaching_experiments(
      id {idcol},user_id INTEGER NOT NULL,tip_id INTEGER NOT NULL,
      baseline_live_session_id INTEGER NOT NULL,followup_live_session_id INTEGER,
      platform TEXT NOT NULL,target_metric TEXT NOT NULL,direction TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'waiting_followup',baseline_value REAL,followup_value REAL,
      delta REAL,percent_change REAL,result TEXT NOT NULL DEFAULT 'insufficient_evidence',
      baseline_sample_size INTEGER NOT NULL DEFAULT 0,followup_sample_size INTEGER NOT NULL DEFAULT 0,
      confidence REAL NOT NULL DEFAULT 0,uncertainty TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(user_id,tip_id)
    )''')
    _exec_migration(con,'CREATE INDEX IF NOT EXISTS idx_coaching_experiment_user ON coaching_experiments(user_id,status,updated_at)')
    try:
        if not con.execute("SELECT id FROM checklist WHERE id='C014'").fetchone():
            con.execute('INSERT INTO checklist(id,title,done,notes) VALUES(?,?,?,?)',('C014','Persistent Coaching Experiment Comparison',1,'Implemented: auto-link comparable follow-up sessions and measure behavior/evidence-quality changes.'));con.commit()
    except Exception:con.rollback()
def _insert_id(con,sql,params):
    from storage import insert_id
    return insert_id(con,sql,params)
def start_session(con,user_id:int,platform:str,source='authorized_capture'):
    ts=now_iso();sid=_insert_id(con,'INSERT INTO live_sessions(user_id,platform,started_at,status,source,created_at) VALUES(?,?,?,?,?,?)',(user_id,platform,ts,'active',source,ts));con.commit();return sid
def append_event(con,*,user_id:int,session_id:int,platform:str,event_type:str,source:str,evidence_type:str,confidence:float,payload=None,source_event_id=None,event_time=None):
    if evidence_type not in EVIDENCE:raise ValueError('invalid evidence_type')
    if evidence_type=='exact_telemetry' and platform!='fsa':raise ValueError('exact_telemetry is reserved for the owned F.S.A. adapter')
    if platform=='fsa' and evidence_type!='exact_telemetry':raise ValueError('F.S.A. adapter requires exact_telemetry')
    confidence=max(0.0,min(1.0,float(confidence)));payload=payload if isinstance(payload,dict) else {}
    eid=_insert_id(con,'INSERT INTO normalized_events(live_session_id,user_id,source_event_id,event_time,platform,event_type,source,evidence_type,confidence,payload_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(session_id,user_id,source_event_id,event_time or now_iso(),platform,event_type,source,evidence_type,confidence,json.dumps(payload),now_iso()))
    update_baseline(con,user_id,platform,event_type,payload);con.commit();refresh_live_tip(con,user_id,session_id);refresh_experiments(con,user_id,session_id);con.commit();return eid
def _event_rows(con,user_id,session_id):return rowsdict(con.execute('SELECT * FROM normalized_events WHERE user_id=? AND live_session_id=? ORDER BY event_time,id',(user_id,session_id)).fetchall())
def _payload(r):
    try:return json.loads(r.get('payload_json') or '{}')
    except Exception:return {}
def _credit_delta(r):
    p=_payload(r);typ=r.get('event_type');v=0.0
    if typ=='credit_change':
        try:
            amount=float(p.get('amount',0) or 0);v+=amount if p.get('direction') in ('grant','win','in','up') else -amount
        except Exception:pass
    if 'creditDelta' in p:
        try:v+=float(p.get('creditDelta') or 0)
        except Exception:pass
    return v
def _seconds(a,b):
    try:return max(0.0,(datetime.fromisoformat(str(b).replace('Z','+00:00'))-datetime.fromisoformat(str(a).replace('Z','+00:00'))).total_seconds())
    except Exception:return 0.0
def metrics(con,user_id:int,session_id:int):
    rows=_event_rows(con,user_id,session_id);shots=sum(r['event_type']=='shot_fired' for r in rows);hits=sum(r['event_type']=='target_hit' for r in rows);kills=sum(r['event_type']=='target_destroyed' for r in rows);breaks=sum(r['event_type'] in ('break','session_break') for r in rows);credit=sum(_credit_delta(r) for r in rows);motions=[]
    for r in rows:
        if r['event_type']=='motion_sample':
            try:motions.append(float(_payload(r).get('motion',0) or 0))
            except Exception:pass
    duration=_seconds(rows[0]['event_time'],rows[-1]['event_time']) if len(rows)>1 else 0
    return {'schema':SCHEMA,'events':len(rows),'shots':shots,'hits':hits,'kills':kills,'breaks':breaks,'hit_rate':hits/shots if shots else 0,'credit_delta':round(credit,4),'duration_min':round(duration/60,2),'shots_per_min':round(shots/(duration/60),2) if duration>=30 else 0,'mean_motion':sum(motions)/len(motions) if motions else 0,'motion_samples':len(motions)}
def analyze_session(con,user_id:int,session_id:int):
    rows=_event_rows(con,user_id,session_id);m=metrics(con,user_id,session_id)
    if not rows:return {'schema':ANALYSIS_SCHEMA,'sessionId':session_id,'metrics':m,'quality':{'confidence':0,'sampleSize':0,'evidenceType':'unknown','completeness':0},'patterns':[],'coaching':[],'uncertainty':'No session evidence recorded yet.'}
    weights={'exact_telemetry':1.0,'observed_evidence':.92,'estimate':.58,'correlation':.45,'hypothesis':.3,'unknown':.15};mean_conf=sum(max(0,min(1,float(r.get('confidence',0))))*weights.get(r.get('evidence_type'),.15) for r in rows)/len(rows);completeness=min(1,len(rows)/20);confidence=round(mean_conf*(.55+.45*completeness),3)
    kinds={r.get('evidence_type') for r in rows};etype='exact_telemetry' if kinds=={'exact_telemetry'} else ('observed_evidence' if kinds<={'observed_evidence'} else 'mixed_evidence')
    patterns=[];coaching=[]
    def add(pid,title,body,conf,evidence='correlation',target='decision_quality'):
        patterns.append({'id':pid,'title':title,'body':body,'evidenceType':evidence,'confidence':round(min(confidence,conf),3),'sampleSize':len(rows)});coaching.append({'id':'coach-'+pid,'title':title,'action':body,'targetMetric':target,'confidence':round(min(confidence,conf),3),'evidenceType':evidence})
    if m['credit_delta']<0:add('negative_net','Recorded credits moved down','Your recorded session is net negative. Pause and review before deciding whether to continue; this describes the session and does not predict the next outcome.',.95,'observed_evidence','decision_review')
    if len(rows)>=8 and m['duration_min']>=2:
        mid=len(rows)//2;a=rows[:mid];b=rows[mid:];da=_seconds(a[0]['event_time'],a[-1]['event_time']);db=_seconds(b[0]['event_time'],b[-1]['event_time']);sa=sum(x['event_type']=='shot_fired' for x in a);sb=sum(x['event_type']=='shot_fired' for x in b);pa=sa/(da/60) if da>=30 else 0;pb=sb/(db/60) if db>=30 else 0;ca=sum(_credit_delta(x) for x in a);cb=sum(_credit_delta(x) for x in b)
        if pa>0 and pb>pa*1.2 and cb<ca:add('pace_up_results_down','Pace increased while recorded results weakened','Your second-half shot pace rose while recorded credit movement weakened. Try a slower, more deliberate pace next session and compare the same pace metric. This is a within-session correlation, not a prediction.',.82,'correlation','shots_per_min')
    running=peak=0.0;max_dd=0.0
    for r in rows:running+=_credit_delta(r);peak=max(peak,running);max_dd=max(max_dd,peak-running)
    if max_dd>0 and max_dd>=max(20,abs(m['credit_delta'])*.5):add('drawdown','Meaningful recorded drawdown','A meaningful peak-to-trough decline appeared in recorded credits. Use a predetermined stop/review limit next session and compare recorded drawdown as a risk-control metric, not as a prediction.',.88,'observed_evidence','max_drawdown')
    if m['duration_min']>=30 and not m['breaks']:add('no_break','Long session with no recorded break','No break was recorded during a longer session. Add a planned break and compare the number of recorded breaks and decision quality afterward.',.9,'observed_evidence','breaks')
    if not coaching:coaching.append({'id':'coach-baseline','title':'Build a stronger baseline','action':'Keep recording consistent evidence across comparable sessions. Avoid treating a short run or apparent streak as predictive.','targetMetric':'evidence_completeness','confidence':confidence,'evidenceType':'observed_evidence'})
    return {'schema':ANALYSIS_SCHEMA,'sessionId':session_id,'platform':rows[-1].get('platform'),'generatedAt':now_iso(),'metrics':{**m,'max_drawdown':round(max_dd,4)},'quality':{'confidence':confidence,'sampleSize':len(rows),'evidenceType':etype,'meanReliability':round(mean_conf,3),'completeness':round(completeness,3)},'patterns':patterns,'coaching':coaching,'uncertainty':'Analysis describes authorized recorded evidence only. Correlation is not causation; no random outcome or hidden server state is predicted.'}
def _metric_value(a,target):
    if target=='evidence_completeness':return float(a.get('quality',{}).get('completeness',0))
    if target in a.get('metrics',{}):return float(a['metrics'].get(target,0) or 0)
    return None
def _ensure_experiment(con,user_id,tip_id,session_id,a,c):
    target=c.get('targetMetric');rule=EXPERIMENT_METRICS.get(target)
    if not rule:return None
    value=_metric_value(a,target);q=a.get('quality',{});row=rowdict(con.execute('SELECT * FROM coaching_experiments WHERE user_id=? AND tip_id=?',(user_id,tip_id)).fetchone())
    if row:
        if not row.get('followup_live_session_id'):
            con.execute('UPDATE coaching_experiments SET platform=?,target_metric=?,direction=?,baseline_value=?,baseline_sample_size=?,confidence=?,updated_at=? WHERE id=?',(a.get('platform') or 'generic',target,rule['direction'],value,int(q.get('sampleSize',0)),float(q.get('confidence',0)),now_iso(),row['id']))
        return row['id']
    return _insert_id(con,'INSERT INTO coaching_experiments(user_id,tip_id,baseline_live_session_id,platform,target_metric,direction,status,baseline_value,result,baseline_sample_size,confidence,uncertainty,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(user_id,tip_id,session_id,a.get('platform') or 'generic',target,rule['direction'],'waiting_followup',value,'insufficient_evidence',int(q.get('sampleSize',0)),float(q.get('confidence',0)),'Waiting for a later comparable session with sufficient evidence.',now_iso(),now_iso()))
def refresh_live_tip(con,user_id:int,session_id:int):
    a=analyze_session(con,user_id,session_id)
    if not a['coaching']:return a
    c=a['coaching'][0];q=a['quality'];level='high' if q['confidence']>=.78 else ('medium' if q['confidence']>=.5 else 'low');evidence=json.dumps({'analysisSchema':a['schema'],'liveSessionId':session_id,'metrics':a['metrics'],'quality':q,'pattern':a['patterns'][0] if a['patterns'] else None,'targetMetric':c.get('targetMetric')},separators=(',',':'))
    existing=rowdict(con.execute('SELECT id FROM tips WHERE user_id=? AND live_session_id=? ORDER BY id DESC LIMIT 1',(user_id,session_id)).fetchone());vals=(now_iso(),c['title'],c['action'],evidence,level,c['evidenceType'],q['sampleSize'],a['uncertainty'])
    if existing:tip_id=existing['id'];con.execute('UPDATE tips SET created_at=?,title=?,body=?,evidence=?,confidence=?,evidence_type=?,sample_size=?,uncertainty=? WHERE id=?',vals+(tip_id,))
    else:tip_id=_insert_id(con,'INSERT INTO tips(user_id,session_id,created_at,title,body,evidence,confidence,live_session_id,evidence_type,sample_size,uncertainty) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(user_id,None,*vals[:5],session_id,*vals[5:]))
    _ensure_experiment(con,user_id,tip_id,session_id,a,c);return a
def _threshold(target,baseline):
    if target=='shots_per_min':return max(.5,abs(baseline)*.10)
    if target=='max_drawdown':return max(5.0,abs(baseline)*.10)
    if target=='breaks':return 1.0
    if target=='evidence_completeness':return .10
    return 0.0
def _classify(target,direction,baseline,followup):
    delta=followup-baseline;tol=_threshold(target,baseline)
    if target=='breaks':return 'improved' if followup>baseline else ('worsened' if followup<baseline else 'unchanged')
    if abs(delta)<tol:return 'unchanged'
    if direction=='lower_better':return 'improved' if delta<0 else 'worsened'
    return 'improved' if delta>0 else 'worsened'
def refresh_experiments(con,user_id:int,current_session_id:int):
    current=rowdict(con.execute('SELECT * FROM live_sessions WHERE id=? AND user_id=?',(current_session_id,user_id)).fetchone())
    if not current:return []
    follow=analyze_session(con,user_id,current_session_id);fq=follow.get('quality',{});rows=rowsdict(con.execute("SELECT * FROM coaching_experiments WHERE user_id=? AND baseline_live_session_id<>? AND status IN ('waiting_followup','collecting') ORDER BY id",(user_id,current_session_id)).fetchall());changed=[]
    for ex in rows:
        if ex.get('platform')!=current.get('platform'):continue
        target=ex.get('target_metric');fv=_metric_value(follow,target)
        if fv is None:continue
        follow_n=int(fq.get('sampleSize',0));base_n=int(ex.get('baseline_sample_size',0));conf=min(float(ex.get('confidence',0) or 0),float(fq.get('confidence',0) or 0));status='collecting';result='insufficient_evidence';uncertainty='More comparable evidence is required before classifying the change.';delta=pct=None
        if base_n>=8 and follow_n>=8 and conf>=.45:
            bv=float(ex.get('baseline_value') or 0);delta=fv-bv;pct=(delta/abs(bv)*100) if abs(bv)>.000001 else None;result=_classify(target,ex.get('direction'),bv,fv);status='completed';uncertainty='This comparison measures recorded behavior/evidence quality across two sessions. It does not prove causation or predict random outcomes.'
        con.execute('UPDATE coaching_experiments SET followup_live_session_id=?,followup_value=?,delta=?,percent_change=?,result=?,followup_sample_size=?,confidence=?,status=?,uncertainty=?,updated_at=? WHERE id=?',(current_session_id,fv,delta,pct,result,follow_n,conf,status,uncertainty,now_iso(),ex['id']));changed.append(ex['id'])
    return changed
def list_experiments(con,user_id:int,limit=50):
    rows=rowsdict(con.execute('SELECT e.*,t.title tip_title,t.body tip_body FROM coaching_experiments e LEFT JOIN tips t ON t.id=e.tip_id WHERE e.user_id=? ORDER BY e.id DESC LIMIT ?',(user_id,int(limit))).fetchall())
    for r in rows:r['schema']=EXPERIMENT_SCHEMA;r['resultLabel']={'improved':'Improved','worsened':'Worsened','unchanged':'Unchanged','insufficient_evidence':'Insufficient Evidence'}.get(r.get('result'),r.get('result'));r['metricLabel']=EXPERIMENT_METRICS.get(r.get('target_metric'),{}).get('label',r.get('target_metric'))
    return rows
def update_baseline(con,user_id,platform,event_type,payload):
    r=rowdict(con.execute('SELECT * FROM learning_baselines WHERE user_id=? AND platform=?',(user_id,platform)).fetchone())
    if r:events=int(r['events']);shots=int(r['shots']);kills=int(r['kills']);credit=float(r.get('credit_delta') or 0);mean_motion=float(r['mean_motion']);motion_n=int(r['motion_n']);counts=json.loads(r.get('type_counts_json') or '{}')
    else:events=shots=kills=motion_n=0;credit=mean_motion=0.0;counts={}
    events+=1;counts[event_type]=counts.get(event_type,0)+1
    if event_type=='shot_fired':shots+=1
    if event_type=='target_destroyed':kills+=1
    if 'creditDelta' in payload:
        try:credit+=float(payload.get('creditDelta') or 0)
        except Exception:pass
    if event_type=='motion_sample':m=float(payload.get('motion',0) or 0);motion_n+=1;mean_motion+=(m-mean_motion)/motion_n
    if r:con.execute('UPDATE learning_baselines SET events=?,shots=?,kills=?,credit_delta=?,mean_motion=?,motion_n=?,type_counts_json=?,updated_at=? WHERE user_id=? AND platform=?',(events,shots,kills,credit,mean_motion,motion_n,json.dumps(counts),now_iso(),user_id,platform))
    else:con.execute('INSERT INTO learning_baselines(user_id,platform,events,shots,kills,credit_delta,mean_motion,motion_n,type_counts_json,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(user_id,platform,events,shots,kills,credit,mean_motion,motion_n,json.dumps(counts),now_iso()))
def context_pack(con,user_id:int):
    rows=rowsdict(con.execute('SELECT * FROM learning_baselines WHERE user_id=?',(user_id,)).fetchall());experiments=list_experiments(con,user_id,10)
    return {'schema':'egm.llm.context.v2','generatedAt':now_iso(),'userId':user_id,'evidenceRules':['exact telemetry is exact only for the owned/authorized F.S.A. source','observed evidence is visible/user-verified','estimates are not hidden-state facts','correlation is not causation','coaching experiments evaluate behavior/evidence quality, not random outcome predictability','never guarantee profit or random outcomes'],'baselines':rows,'coachingExperiments':experiments}
