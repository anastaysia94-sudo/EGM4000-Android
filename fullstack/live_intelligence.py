from __future__ import annotations
import json, math
from datetime import datetime,timezone
from storage import rowdict,rowsdict
SCHEMA='egm.event.v1'
ANALYSIS_SCHEMA='egm.analysis.v1'
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
def now_iso():return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def _exec_migration(con,sql):
    try:con.execute(sql);con.commit()
    except Exception:con.rollback()
def migrate(con):
    # Additive migration only. Existing databases remain valid.
    for sql in (
      'ALTER TABLE tips ADD COLUMN live_session_id INTEGER',
      "ALTER TABLE tips ADD COLUMN evidence_type TEXT NOT NULL DEFAULT 'observed_evidence'",
      'ALTER TABLE tips ADD COLUMN sample_size INTEGER NOT NULL DEFAULT 0',
      "ALTER TABLE tips ADD COLUMN uncertainty TEXT NOT NULL DEFAULT ''",
    ):_exec_migration(con,sql)
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
    update_baseline(con,user_id,platform,event_type,payload);con.commit();refresh_live_tip(con,user_id,session_id);con.commit();return eid
def _event_rows(con,user_id,session_id):
    return rowsdict(con.execute('SELECT * FROM normalized_events WHERE user_id=? AND live_session_id=? ORDER BY event_time,id',(user_id,session_id)).fetchall())
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
    if not rows:return {'schema':ANALYSIS_SCHEMA,'sessionId':session_id,'metrics':m,'quality':{'confidence':0,'sampleSize':0,'evidenceType':'unknown'},'patterns':[],'coaching':[],'uncertainty':'No session evidence recorded yet.'}
    weights={'exact_telemetry':1.0,'observed_evidence':.92,'estimate':.58,'correlation':.45,'hypothesis':.3,'unknown':.15};mean_conf=sum(max(0,min(1,float(r.get('confidence',0))))*weights.get(r.get('evidence_type'),.15) for r in rows)/len(rows);completeness=min(1,len(rows)/20);confidence=round(mean_conf*(.55+.45*completeness),3)
    kinds={r.get('evidence_type') for r in rows};etype='exact_telemetry' if kinds=={'exact_telemetry'} else ('observed_evidence' if kinds<= {'observed_evidence'} else 'mixed_evidence')
    patterns=[];coaching=[]
    def add(pid,title,body,conf,evidence='correlation',target='decision_quality'):
        patterns.append({'id':pid,'title':title,'body':body,'evidenceType':evidence,'confidence':round(min(confidence,conf),3),'sampleSize':len(rows)});coaching.append({'id':'coach-'+pid,'title':title,'action':body,'targetMetric':target,'confidence':round(min(confidence,conf),3),'evidenceType':evidence})
    if m['credit_delta']<0:add('negative_net','Recorded credits moved down','Your recorded session is net negative. Pause and review before deciding whether to continue; this describes the session and does not predict the next outcome.',.95,'observed_evidence','credit_delta')
    # Compare shot pace in first and second halves only when timestamps are sufficiently spread.
    if len(rows)>=8 and m['duration_min']>=2:
        mid=len(rows)//2;a=rows[:mid];b=rows[mid:];da=_seconds(a[0]['event_time'],a[-1]['event_time']);db=_seconds(b[0]['event_time'],b[-1]['event_time']);sa=sum(x['event_type']=='shot_fired' for x in a);sb=sum(x['event_type']=='shot_fired' for x in b);pa=sa/(da/60) if da>=30 else 0;pb=sb/(db/60) if db>=30 else 0;ca=sum(_credit_delta(x) for x in a);cb=sum(_credit_delta(x) for x in b)
        if pa>0 and pb>pa*1.2 and cb<ca:add('pace_up_results_down','Pace increased while recorded results weakened','Your second-half shot pace rose while recorded credit movement weakened. Try a slower, more deliberate pace next session and compare the same metric. This is a within-session correlation, not a prediction.',.82,'correlation','shots_per_min')
    running=peak=0.0;max_dd=0.0
    for r in rows:
        running+=_credit_delta(r);peak=max(peak,running);max_dd=max(max_dd,peak-running)
    if max_dd>0 and (max_dd>=max(20,abs(m['credit_delta'])*.5)):
        add('drawdown','Meaningful recorded drawdown','A meaningful peak-to-trough decline appeared in the recorded credits. Consider a predetermined stop/review limit before the next session.',.88,'observed_evidence','max_drawdown')
    if m['duration_min']>=30 and not m['breaks']:add('no_break','Long session with no recorded break','No break was recorded during a longer session. Add a planned break and compare pace and decision quality afterward.',.9,'observed_evidence','breaks')
    if not coaching:coaching.append({'id':'coach-baseline','title':'Build a stronger baseline','action':'Keep recording consistent evidence across comparable sessions. Avoid treating a short run or apparent streak as predictive.','targetMetric':'evidence_completeness','confidence':confidence,'evidenceType':'observed_evidence'})
    return {'schema':ANALYSIS_SCHEMA,'sessionId':session_id,'platform':rows[-1].get('platform'),'generatedAt':now_iso(),'metrics':{**m,'max_drawdown':round(max_dd,4)},'quality':{'confidence':confidence,'sampleSize':len(rows),'evidenceType':etype,'meanReliability':round(mean_conf,3),'completeness':round(completeness,3)},'patterns':patterns,'coaching':coaching,'uncertainty':'Analysis describes authorized recorded evidence only. Correlation is not causation; no random outcome or hidden server state is predicted.'}
def refresh_live_tip(con,user_id:int,session_id:int):
    a=analyze_session(con,user_id,session_id)
    if not a['coaching']:return a
    c=a['coaching'][0];q=a['quality'];level='high' if q['confidence']>=.78 else ('medium' if q['confidence']>=.5 else 'low');evidence=json.dumps({'analysisSchema':a['schema'],'liveSessionId':session_id,'metrics':a['metrics'],'quality':q,'pattern':a['patterns'][0] if a['patterns'] else None},separators=(',',':'))
    existing=rowdict(con.execute('SELECT id FROM tips WHERE user_id=? AND live_session_id=? ORDER BY id DESC LIMIT 1',(user_id,session_id)).fetchone())
    vals=(now_iso(),c['title'],c['action'],evidence,level,c['evidenceType'],q['sampleSize'],a['uncertainty'])
    if existing:con.execute('UPDATE tips SET created_at=?,title=?,body=?,evidence=?,confidence=?,evidence_type=?,sample_size=?,uncertainty=? WHERE id=?',vals+(existing['id'],))
    else:_insert_id(con,'INSERT INTO tips(user_id,session_id,created_at,title,body,evidence,confidence,live_session_id,evidence_type,sample_size,uncertainty) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(user_id,None,*vals[:5],session_id,*vals[5:]))
    return a
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
    if event_type=='motion_sample':
        m=float(payload.get('motion',0) or 0);motion_n+=1;mean_motion+=(m-mean_motion)/motion_n
    if r:con.execute('UPDATE learning_baselines SET events=?,shots=?,kills=?,credit_delta=?,mean_motion=?,motion_n=?,type_counts_json=?,updated_at=? WHERE user_id=? AND platform=?',(events,shots,kills,credit,mean_motion,motion_n,json.dumps(counts),now_iso(),user_id,platform))
    else:con.execute('INSERT INTO learning_baselines(user_id,platform,events,shots,kills,credit_delta,mean_motion,motion_n,type_counts_json,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(user_id,platform,events,shots,kills,credit,mean_motion,motion_n,json.dumps(counts),now_iso()))
def context_pack(con,user_id:int):
    rows=rowsdict(con.execute('SELECT * FROM learning_baselines WHERE user_id=?',(user_id,)).fetchall())
    return {'schema':'egm.llm.context.v1','generatedAt':now_iso(),'userId':user_id,'evidenceRules':['exact telemetry is exact only for the owned/authorized F.S.A. source','observed evidence is visible/user-verified','estimates are not hidden-state facts','correlation is not causation','never guarantee profit or random outcomes'],'baselines':rows}
