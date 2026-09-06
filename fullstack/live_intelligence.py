from __future__ import annotations
import json
from datetime import datetime,timezone
from storage import rowdict,rowsdict
SCHEMA='egm.event.v1'
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
def migrate(con):return None
def _insert_id(con,sql,params):
    from storage import insert_id
    return insert_id(con,sql,params)
def start_session(con,user_id:int,platform:str,source='authorized_capture'):
    ts=now_iso();sid=_insert_id(con,'INSERT INTO live_sessions(user_id,platform,started_at,status,source,created_at) VALUES(?,?,?,?,?,?)',(user_id,platform,ts,'active',source,ts));con.commit();return sid
def append_event(con,*,user_id:int,session_id:int,platform:str,event_type:str,source:str,evidence_type:str,confidence:float,payload=None,source_event_id=None,event_time=None):
    if evidence_type not in EVIDENCE:raise ValueError('invalid evidence_type')
    confidence=max(0.0,min(1.0,float(confidence)));payload=payload if isinstance(payload,dict) else {}
    eid=_insert_id(con,'INSERT INTO normalized_events(live_session_id,user_id,source_event_id,event_time,platform,event_type,source,evidence_type,confidence,payload_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',(session_id,user_id,source_event_id,event_time or now_iso(),platform,event_type,source,evidence_type,confidence,json.dumps(payload),now_iso()))
    update_baseline(con,user_id,platform,event_type,payload);con.commit();return eid
def metrics(con,user_id:int,session_id:int):
    rows=con.execute('SELECT event_type,payload_json FROM normalized_events WHERE user_id=? AND live_session_id=? ORDER BY id',(user_id,session_id)).fetchall();shots=hits=kills=0;credit=0.0;motions=[]
    for raw in rows:
        r=rowdict(raw);typ=r['event_type'];shots+=typ=='shot_fired';hits+=typ=='target_hit';kills+=typ=='target_destroyed'
        try:p=json.loads(r.get('payload_json') or '{}')
        except Exception:p={}
        if typ=='credit_change':
            amount=float(p.get('amount',0) or 0);credit+=amount if p.get('direction') in ('grant','win','in','up') else -amount
        if 'creditDelta' in p:
            try:credit+=float(p.get('creditDelta') or 0)
            except Exception:pass
        if typ=='motion_sample':
            try:motions.append(float(p.get('motion',0) or 0))
            except Exception:pass
    return {'schema':SCHEMA,'events':len(rows),'shots':shots,'hits':hits,'kills':kills,'hit_rate':hits/shots if shots else 0,'credit_delta':round(credit,4),'mean_motion':sum(motions)/len(motions) if motions else 0,'motion_samples':len(motions)}
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
    if r:
        con.execute('UPDATE learning_baselines SET events=?,shots=?,kills=?,credit_delta=?,mean_motion=?,motion_n=?,type_counts_json=?,updated_at=? WHERE user_id=? AND platform=?',(events,shots,kills,credit,mean_motion,motion_n,json.dumps(counts),now_iso(),user_id,platform))
    else:
        con.execute('INSERT INTO learning_baselines(user_id,platform,events,shots,kills,credit_delta,mean_motion,motion_n,type_counts_json,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)',(user_id,platform,events,shots,kills,credit,mean_motion,motion_n,json.dumps(counts),now_iso()))
def context_pack(con,user_id:int):
    rows=rowsdict(con.execute('SELECT * FROM learning_baselines WHERE user_id=?',(user_id,)).fetchall())
    return {'schema':'egm.llm.context.v1','generatedAt':now_iso(),'userId':user_id,'evidenceRules':['exact telemetry is exact only for an authorized exact source','observed evidence is visible/user-verified','estimates are not hidden-state facts','correlation is not causation','never guarantee profit or random outcomes'],'baselines':rows}
