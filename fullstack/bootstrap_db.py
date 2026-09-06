#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timedelta, timezone
import base64,csv,hashlib,json,os,random,secrets
from storage import connect, scalar, POSTGRES

ROOT=Path(__file__).resolve().parent; DATA=ROOT/'data'; CREDS=DATA/'seed_users_credentials.generated.csv'
OWNER_USERNAME=os.environ.get('EGM_OWNER_USERNAME','EGM4000Owner')
OWNER_PASSWORD=os.environ.get('EGM_OWNER_PASSWORD')
PLATFORMS=['Fire Kirin','GameVault','Panda Master','Juwa']
FOCUS=['target selection','shot efficiency','session length','bankroll discipline','bonus-event logging','evidence review']

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def hash_password(password):
    salt=os.urandom(16); digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,240_000)
    return base64.b64encode(digest).decode(),base64.b64encode(salt).decode()

def schema_sql(postgres=False):
    idcol='SERIAL PRIMARY KEY' if postgres else 'INTEGER PRIMARY KEY AUTOINCREMENT'
    return f'''
CREATE TABLE IF NOT EXISTS users(id {idcol},username TEXT UNIQUE NOT NULL,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,salt TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'user',display_name TEXT NOT NULL,bio TEXT NOT NULL DEFAULT '',favorite_platform TEXT,skill_focus TEXT,joined_at TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'active',is_synthetic INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS auth_sessions(token TEXT PRIMARY KEY,user_id INTEGER NOT NULL,csrf TEXT NOT NULL,created_at TEXT NOT NULL,expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS mobile_tokens(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL,created_at TEXT NOT NULL,expires_at TEXT NOT NULL,last_used_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS gameplay_sessions(id {idcol},user_id INTEGER NOT NULL,platform TEXT NOT NULL,started_at TEXT NOT NULL,duration_min INTEGER,starting_bankroll REAL,spend REAL,payout REAL,shots INTEGER,hits INTEGER,notes TEXT,source TEXT NOT NULL DEFAULT 'synthetic_seed');
CREATE TABLE IF NOT EXISTS tips(id {idcol},user_id INTEGER NOT NULL,session_id INTEGER,created_at TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,evidence TEXT NOT NULL,confidence TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS forum_threads(id {idcol},user_id INTEGER NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,category TEXT NOT NULL DEFAULT 'General',status TEXT NOT NULL DEFAULT 'published',pinned INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS forum_replies(id {idcol},thread_id INTEGER NOT NULL,user_id INTEGER NOT NULL,body TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'published',created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS blog_posts(id {idcol},user_id INTEGER NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,tags TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'pending',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS blog_comments(id {idcol},post_id INTEGER NOT NULL,user_id INTEGER NOT NULL,body TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'published',created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reactions(id {idcol},user_id INTEGER NOT NULL,target_type TEXT NOT NULL,target_id INTEGER NOT NULL,reaction TEXT NOT NULL DEFAULT 'like',created_at TEXT NOT NULL,UNIQUE(user_id,target_type,target_id));
CREATE TABLE IF NOT EXISTS reports(id {idcol},reporter_user_id INTEGER,target_type TEXT NOT NULL,target_id INTEGER NOT NULL,reason TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open',resolution TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,resolved_at TEXT);
CREATE TABLE IF NOT EXISTS surveys(id {idcol},title TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',audience TEXT NOT NULL DEFAULT 'all',status TEXT NOT NULL DEFAULT 'active',frequency_days INTEGER NOT NULL DEFAULT 30,starts_at TEXT,ends_at TEXT,created_by INTEGER NOT NULL,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS survey_questions(id {idcol},survey_id INTEGER NOT NULL,prompt TEXT NOT NULL,kind TEXT NOT NULL DEFAULT 'scale',options_json TEXT NOT NULL DEFAULT '[]',position INTEGER NOT NULL DEFAULT 0,required INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS visitor_profiles(visitor_hash TEXT PRIMARY KEY,network_hash TEXT NOT NULL DEFAULT '',first_seen_at TEXT NOT NULL,last_seen_at TEXT NOT NULL,visit_count INTEGER NOT NULL DEFAULT 1,consent INTEGER NOT NULL DEFAULT 0,user_id INTEGER);
CREATE TABLE IF NOT EXISTS survey_responses(id {idcol},survey_id INTEGER NOT NULL,user_id INTEGER,visitor_hash TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS survey_answers(id {idcol},response_id INTEGER NOT NULL,question_id INTEGER NOT NULL,answer_text TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS admin_features(id TEXT PRIMARY KEY,title TEXT NOT NULL,category TEXT NOT NULL,implementation_status TEXT NOT NULL DEFAULT 'modelled');
CREATE TABLE IF NOT EXISTS monetization_channels(id TEXT PRIMARY KEY,title TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 0,provider_status TEXT NOT NULL DEFAULT 'configuration_required');
CREATE TABLE IF NOT EXISTS return_features(id TEXT PRIMARY KEY,title TEXT NOT NULL,implementation_status TEXT NOT NULL DEFAULT 'modelled');
CREATE TABLE IF NOT EXISTS checklist(id TEXT PRIMARY KEY,title TEXT NOT NULL,done INTEGER NOT NULL DEFAULT 0,notes TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS audit_events(id {idcol},actor_user_id INTEGER,action TEXT NOT NULL,target_type TEXT,target_id TEXT,details_json TEXT NOT NULL DEFAULT '{{}}',created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS live_sessions(id {idcol},user_id INTEGER NOT NULL,platform TEXT NOT NULL,started_at TEXT NOT NULL,ended_at TEXT,status TEXT NOT NULL DEFAULT 'active',source TEXT NOT NULL DEFAULT 'authorized_capture',created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS normalized_events(id {idcol},live_session_id INTEGER NOT NULL,user_id INTEGER NOT NULL,source_event_id TEXT,event_time TEXT NOT NULL,platform TEXT NOT NULL,event_type TEXT NOT NULL,source TEXT NOT NULL,evidence_type TEXT NOT NULL,confidence REAL NOT NULL DEFAULT 0,payload_json TEXT NOT NULL DEFAULT '{{}}',created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS learning_baselines(user_id INTEGER NOT NULL,platform TEXT NOT NULL,events INTEGER NOT NULL DEFAULT 0,shots INTEGER NOT NULL DEFAULT 0,kills INTEGER NOT NULL DEFAULT 0,credit_delta REAL NOT NULL DEFAULT 0,mean_motion REAL NOT NULL DEFAULT 0,motion_n INTEGER NOT NULL DEFAULT 0,type_counts_json TEXT NOT NULL DEFAULT '{{}}',updated_at TEXT NOT NULL,PRIMARY KEY(user_id,platform));
'''

def execute_script(con, script):
    for stmt in [s.strip() for s in script.split(';') if s.strip()]: con.execute(stmt)

def insert_with_id(con, table, cols, vals, explicit_id=None):
    names=list(cols); values=list(vals)
    if explicit_id is not None: names=['id']+names; values=[explicit_id]+values
    qs=','.join('?' for _ in names)
    con.execute(f"INSERT INTO {table}({','.join(names)}) VALUES({qs})",tuple(values))

def ensure_schema(con):
    execute_script(con,schema_sql(con.postgres)); con.commit()
    try:
        con.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_norm_source_event ON normalized_events(source_event_id) WHERE source_event_id IS NOT NULL')
        con.execute('CREATE INDEX IF NOT EXISTS idx_thread_created ON forum_threads(created_at)')
        con.execute('CREATE INDEX IF NOT EXISTS idx_blog_created ON blog_posts(created_at)')
        con.commit()
    except Exception:
        con.rollback()

def seed(con):
    if scalar(con,'SELECT COUNT(*) FROM users'):
        return False
    if not OWNER_PASSWORD: raise SystemExit('Set EGM_OWNER_PASSWORD before first bootstrap.')
    oh,osalt=hash_password(OWNER_PASSWORD)
    insert_with_id(con,'users',['username','email','password_hash','salt','role','display_name','bio','favorite_platform','skill_focus','joined_at','status','is_synthetic'],[OWNER_USERNAME,'owner@egm4000.local',oh,osalt,'owner','EGM4000 Owner','Owner and administrator of EGM4000.','EGM4000','Administration',now(),'active',0],1)
    generated=[]; session_id=tip_id=1
    for n in range(1,238):
        uid=n+1; platform=PLATFORMS[(n-1)%4]; focus=FOCUS[(n-1)%len(FOCUS)]
        username=f'AquaPilot{n:03d}'; display=f'Aqua Pilot {n:03d}'; email=f'aquapilot{n:03d}@example.test'; pw=f'EGM!{uid:03d}-'+secrets.token_urlsafe(9); ph,salt=hash_password(pw)
        joined=(datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=n%180)).replace(microsecond=0).isoformat()
        bio=f'Fictional EGM4000 seed profile focused on {focus}. Synthetic account for community and analytics testing.'
        insert_with_id(con,'users',['username','email','password_hash','salt','role','display_name','bio','favorite_platform','skill_focus','joined_at','status','is_synthetic'],[username,email,ph,salt,'user',display,bio,platform,focus,joined,'active',1],uid)
        generated.append([uid,username,pw,email,display,platform,focus]); rng=random.Random(4000+n)
        for j,p in enumerate(PLATFORMS):
            started=(datetime(2026,1,5,tzinfo=timezone.utc)+timedelta(days=(n*3+j*11)%220)).isoformat(); shots=rng.randint(280,1750); hits=int(shots*rng.uniform(.10,.31)); spend=round(rng.uniform(5,95),2); payout=round(spend*rng.uniform(.55,1.45),2)
            insert_with_id(con,'gameplay_sessions',['user_id','platform','started_at','duration_min','starting_bankroll','spend','payout','shots','hits','notes','source'],[uid,p,started,rng.randint(18,95),round(rng.uniform(30,180),2),spend,payout,shots,hits,f'Fictional seed session focused on {focus}.','synthetic_seed'],session_id)
            evidence=f'{p}: {shots} shots, {hits} logged hits, spend {spend:.2f}, return {payout:.2f}.'
            insert_with_id(con,'tips',['user_id','session_id','created_at','title','body','evidence','confidence'],[uid,session_id,started,'Compare repeated evidence','Compare several similarly logged sessions before changing play. A single hot or cold run is not predictive.',evidence,'medium'],tip_id)
            session_id+=1;tip_id+=1
        thread_time=(datetime(2026,7,1,tzinfo=timezone.utc)+timedelta(hours=n)).isoformat()
        insert_with_id(con,'forum_threads',['user_id','title','body','category','status','pinned','created_at','updated_at'],[uid,f'{platform} session notes #{n:03d}',f'I am testing how I log {focus}. What evidence do you record so comparisons stay useful?','Session Review','published',0,thread_time,thread_time],n)
        reply_uid=((n)%237)+2
        insert_with_id(con,'forum_replies',['thread_id','user_id','body','status','created_at'],[n,reply_uid,'I compare multiple sessions and keep estimates separate from verified observations.','published',thread_time],n)
        insert_with_id(con,'blog_posts',['user_id','title','body','tags','status','created_at','updated_at'],[uid,f'What I learned from logging {platform}',f'This synthetic community article describes a fictional user testing {focus}. The main lesson is to preserve evidence quality and avoid treating short runs as predictions.',f'{platform},evidence,session-review','published',thread_time,thread_time],n)
        insert_with_id(con,'blog_comments',['post_id','user_id','body','status','created_at'],[n,reply_uid,'Useful reminder to label estimates and keep a longer sample.','published',thread_time],n)
    # surveys
    insert_with_id(con,'surveys',['title','description','audience','status','frequency_days','starts_at','ends_at','created_by','created_at'],['First Visit Pulse','Help shape EGM4000 without exposing raw IP addresses.','first','active',90,None,None,1,now()],1)
    insert_with_id(con,'surveys',['title','description','audience','status','frequency_days','starts_at','ends_at','created_by','created_at'],['Returning Player Check-in','Tell us what brings you back and which evidence tools help most.','returning','active',30,None,None,1,now()],2)
    qid=1
    for sid,prompts in [(1,[('How clear is the first-run tutorial?','scale','[]'),('Which game profile are you most interested in?','choice',json.dumps(PLATFORMS)),('What should EGM explain better?','text','[]')]),(2,[('How useful are session-derived tips?','scale','[]'),('Which feature brought you back today?','choice',json.dumps(['Tips','Replay','Community','Live Lab','Surveys'])),('What should improve next?','text','[]')])]:
        for pos,(prompt,kind,opts) in enumerate(prompts):
            insert_with_id(con,'survey_questions',['survey_id','prompt','kind','options_json','position','required'],[sid,prompt,kind,opts,pos,1],qid); qid+=1
    # feature registries
    for i in range(1,101):
        fid=f'A{i:03d}'; cat='Monetization' if 71<=i<=95 else 'Administration'; status='implemented' if i in (1,2,3,5,7,10,11,12,13,14,16,17,18,19,20,30,31,32,33,46,47,48,49,50,51,52,54,55,56,57,63,64,68,70,96,97,99,100) else ('provider_configuration_required' if 71<=i<=95 else 'modelled')
        con.execute('INSERT INTO admin_features(id,title,category,implementation_status) VALUES(?,?,?,?)',(fid,f'Admin capability {i:03d}',cat,status)); con.execute('INSERT INTO checklist(id,title,done,notes) VALUES(?,?,?,?)',(fid,f'Admin capability {i:03d}',1 if status=='implemented' else 0,''))
        if 71<=i<=95: con.execute('INSERT INTO monetization_channels(id,title,enabled,provider_status) VALUES(?,?,0,?)',(fid,f'Monetization capability {i:03d}','configuration_required'))
    for i in range(1,50):
        rid=f'R{i:03d}'; status='implemented' if i in (1,2,3,4,5,10,11,17,19,20,21,29,30,36,38,40,42,43,44,45,46,47,48,49) else 'modelled'; con.execute('INSERT INTO return_features(id,title,implementation_status) VALUES(?,?,?)',(rid,f'Return-user feature {i:03d}',status)); con.execute('INSERT INTO checklist(id,title,done,notes) VALUES(?,?,?,?)',(rid,f'Return-user feature {i:03d}',1 if status=='implemented' else 0,''))
    core_done={1,2,3,4,5,6,10,11,12}
    for i in range(1,13): con.execute('INSERT INTO checklist(id,title,done,notes) VALUES(?,?,?,?)',(f'C{i:03d}',f'Core milestone {i:03d}',1 if i in core_done else 0,''))
    con.commit()
    if not POSTGRES:
        DATA.mkdir(exist_ok=True)
        with CREDS.open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(['user_id','username','password','email','display_name','favorite_platform','skill_focus']);w.writerows(generated)
        try:os.chmod(CREDS,0o600)
        except OSError:pass
    return True

def bootstrap(force=False):
    if not POSTGRES:
        DATA.mkdir(exist_ok=True)
        db=DATA/'egm4000.db'
        if force and db.exists(): db.unlink()
    con=connect(); ensure_schema(con); created=seed(con); con.close()
    print('EGM4000 schema ready.' + (' Seeded initial data.' if created else ' Existing data preserved.'))

if __name__=='__main__':
    import sys; bootstrap('--force' in sys.argv)
