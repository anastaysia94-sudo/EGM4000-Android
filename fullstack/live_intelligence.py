"""EGM4000 cross-chat live intelligence core.
Framework-neutral SQLite helpers for normalized live evidence and learning baselines.
Third-party platforms are read-only/user-authorized evidence sources. F.S.A. is separate.
"""
from __future__ import annotations
import json, sqlite3
from datetime import datetime, timezone
SCHEMA="egm.event.v1"
EVIDENCE=("exact_telemetry","observed_evidence","estimate","correlation","hypothesis","unknown")
ADAPTERS=({"id":"fire-kirin","name":"Fire Kirin","mode":"observed"},{"id":"panda-master","name":"Panda Master","mode":"observed"},{"id":"orion-stars","name":"Orion Stars","mode":"observed"},{"id":"juwa","name":"Juwa","mode":"observed"},{"id":"game-master","name":"Game Master / GameVault","mode":"observed"},{"id":"generic","name":"Generic Fish Shooter","mode":"observed"},{"id":"fsa","name":"F.S.A. Perfect Telemetry","mode":"exact"})
def now_iso(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def migrate(con:sqlite3.Connection):
 con.executescript("""CREATE TABLE IF NOT EXISTS live_sessions(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,platform TEXT NOT NULL,started_at TEXT NOT NULL,ended_at TEXT,status TEXT NOT NULL DEFAULT 'active',source TEXT NOT NULL DEFAULT 'authorized_capture',created_at TEXT NOT NULL);CREATE TABLE IF NOT EXISTS normalized_events(id INTEGER PRIMARY KEY,live_session_id INTEGER NOT NULL,user_id INTEGER NOT NULL,source_event_id TEXT,event_time TEXT NOT NULL,platform TEXT NOT NULL,event_type TEXT NOT NULL,source TEXT NOT NULL,evidence_type TEXT NOT NULL,confidence REAL NOT NULL DEFAULT 0,payload_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL);CREATE UNIQUE INDEX IF NOT EXISTS idx_norm_source_event ON normalized_events(source_event_id) WHERE source_event_id IS NOT NULL;CREATE TABLE IF NOT EXISTS learning_baselines(user_id INTEGER NOT NULL,platform TEXT NOT NULL,events INTEGER NOT NULL DEFAULT 0,shots INTEGER NOT NULL DEFAULT 0,kills INTEGER NOT NULL DEFAULT 0,credit_delta REAL NOT NULL DEFAULT 0,mean_motion REAL NOT NULL DEFAULT 0,motion_n INTEGER NOT NULL DEFAULT 0,type_counts_json TEXT NOT NULL DEFAULT '{}',updated_at TEXT NOT NULL,PRIMARY KEY(user_id,platform));"""); con.commit()
def start_session(con,user_id:int,platform:str,source="authorized_capture"):
 ts=now_iso(); cur=con.execute("INSERT INTO live_sessions(user_id,platform,started_at,status,source,created_at) VALUES(?,?,?,'active',?,?)",(user_id,platform,ts,source,ts)); con.commit(); return cur.lastrowid
def append_event(con,*,user_id:int,session_id:int,platform:str,event_type:str,source:str,evidence_type:str,confidence:float,payload=None,source_event_id=None,event_time=None):
 if evidence_type not in EVIDENCE: raise ValueError("invalid evidence_type")
 confidence=max(0,min(1,float(confidence))); payload=payload if isinstance(payload,dict) else {}
 cur=con.execute("INSERT INTO normalized_events(live_session_id,user_id,source_event_id,event_time,platform,event_type,source,evidence_type,confidence,payload_json,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",(session_id,user_id,source_event_id,event_time or now_iso(),platform,event_type,source,evidence_type,confidence,json.dumps(payload),now_iso())); update_baseline(con,user_id,platform,event_type,payload); con.commit(); return cur.lastrowid
def metrics(con,user_id:int,session_id:int):
 rows=con.execute("SELECT event_type,payload_json FROM normalized_events WHERE user_id=? AND live_session_id=? ORDER BY id",(user_id,session_id)).fetchall(); shots=sum(r[0]=='shot_fired' for r in rows); hits=sum(r[0]=='target_hit' for r in rows); kills=sum(r[0]=='target_destroyed' for r in rows); motions=[]
 for typ,pj in rows:
  if typ=='motion_sample':
   try: motions.append(float(json.loads(pj or '{}').get('motion',0) or 0))
   except Exception: pass
 return {"schema":SCHEMA,"events":len(rows),"shots":shots,"hits":hits,"kills":kills,"hit_rate":hits/shots if shots else 0,"mean_motion":sum(motions)/len(motions) if motions else 0}
def update_baseline(con,user_id,platform,event_type,payload):
 r=con.execute("SELECT events,shots,kills,mean_motion,motion_n,type_counts_json FROM learning_baselines WHERE user_id=? AND platform=?",(user_id,platform)).fetchone()
 if r: events,shots,kills,mean_motion,motion_n,counts_json=r; counts=json.loads(counts_json or '{}')
 else: events=shots=kills=motion_n=0; mean_motion=0.0; counts={}
 events+=1; counts[event_type]=counts.get(event_type,0)+1
 if event_type=='shot_fired': shots+=1
 if event_type=='target_destroyed': kills+=1
 if event_type=='motion_sample': m=float(payload.get('motion',0) or 0); motion_n+=1; mean_motion+=(m-mean_motion)/motion_n
 con.execute("INSERT INTO learning_baselines(user_id,platform,events,shots,kills,mean_motion,motion_n,type_counts_json,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(user_id,platform) DO UPDATE SET events=excluded.events,shots=excluded.shots,kills=excluded.kills,mean_motion=excluded.mean_motion,motion_n=excluded.motion_n,type_counts_json=excluded.type_counts_json,updated_at=excluded.updated_at",(user_id,platform,events,shots,kills,mean_motion,motion_n,json.dumps(counts),now_iso()))
def context_pack(con,user_id:int):
 rows=con.execute("SELECT platform,events,shots,kills,mean_motion,motion_n,type_counts_json,updated_at FROM learning_baselines WHERE user_id=?",(user_id,)).fetchall(); return {"schema":"egm.llm.context.v1","generatedAt":now_iso(),"userId":user_id,"evidenceRules":["exact is exact only for authorized exact sources","observed evidence is visible/user-verified","estimates are not hidden-state facts","correlation is not causation","never guarantee profit/random outcomes"],"baselines":[list(r) for r in rows]}
