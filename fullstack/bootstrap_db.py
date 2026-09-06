#!/usr/bin/env python3
"""Reproducible public bootstrap for the EGM4000 full-stack reference.

No credentials are committed. Set EGM_OWNER_PASSWORD; fictional test-user
passwords are generated fresh into data/seed_users_credentials.generated.csv.
"""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import base64, csv, hashlib, os, random, secrets, sqlite3

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
DB = DATA / 'egm4000.db'
CREDS = DATA / 'seed_users_credentials.generated.csv'
OWNER_USERNAME = os.environ.get('EGM_OWNER_USERNAME', 'EGM4000Owner')
OWNER_PASSWORD = os.environ.get('EGM_OWNER_PASSWORD')
PLATFORMS = ['Fire Kirin', 'GameVault', 'Panda Master', 'Juwa']
FOCUS = ['target selection','shot efficiency','session length','bankroll discipline','bonus-event logging','evidence review']

SCHEMA = r'''
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, salt TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'user', display_name TEXT NOT NULL, favorite_platform TEXT, skill_focus TEXT, joined_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'active');
CREATE TABLE IF NOT EXISTS auth_sessions(token TEXT PRIMARY KEY,user_id INTEGER NOT NULL,csrf TEXT NOT NULL,created_at TEXT NOT NULL,expires_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS gameplay_sessions(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,platform TEXT NOT NULL,started_at TEXT NOT NULL,duration_min INTEGER,starting_bankroll REAL,spend REAL,payout REAL,shots INTEGER,hits INTEGER,notes TEXT,source TEXT NOT NULL DEFAULT 'synthetic_seed',FOREIGN KEY(user_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS tips(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,session_id INTEGER,created_at TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,evidence TEXT NOT NULL,confidence TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS admin_features(id TEXT PRIMARY KEY,title TEXT NOT NULL,category TEXT NOT NULL,implementation_status TEXT NOT NULL DEFAULT 'modelled');
CREATE TABLE IF NOT EXISTS monetization_channels(id TEXT PRIMARY KEY,title TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 0,provider_status TEXT NOT NULL DEFAULT 'configuration_required');
CREATE TABLE IF NOT EXISTS return_features(id TEXT PRIMARY KEY,title TEXT NOT NULL,implementation_status TEXT NOT NULL DEFAULT 'modelled');
CREATE TABLE IF NOT EXISTS checklist(id TEXT PRIMARY KEY,title TEXT NOT NULL,done INTEGER NOT NULL DEFAULT 0,notes TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS live_sessions(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,platform TEXT NOT NULL,started_at TEXT NOT NULL,ended_at TEXT,status TEXT NOT NULL DEFAULT 'active',source TEXT NOT NULL DEFAULT 'authorized_capture',created_at TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id));
CREATE TABLE IF NOT EXISTS normalized_events(id INTEGER PRIMARY KEY,live_session_id INTEGER NOT NULL,user_id INTEGER NOT NULL,source_event_id TEXT,event_time TEXT NOT NULL,platform TEXT NOT NULL,event_type TEXT NOT NULL,source TEXT NOT NULL,evidence_type TEXT NOT NULL,confidence REAL NOT NULL DEFAULT 0,payload_json TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,FOREIGN KEY(live_session_id) REFERENCES live_sessions(id),FOREIGN KEY(user_id) REFERENCES users(id));
CREATE UNIQUE INDEX IF NOT EXISTS idx_norm_source_event ON normalized_events(source_event_id) WHERE source_event_id IS NOT NULL;
CREATE TABLE IF NOT EXISTS learning_baselines(user_id INTEGER NOT NULL,platform TEXT NOT NULL,events INTEGER NOT NULL DEFAULT 0,shots INTEGER NOT NULL DEFAULT 0,kills INTEGER NOT NULL DEFAULT 0,credit_delta REAL NOT NULL DEFAULT 0,mean_motion REAL NOT NULL DEFAULT 0,motion_n INTEGER NOT NULL DEFAULT 0,type_counts_json TEXT NOT NULL DEFAULT '{}',updated_at TEXT NOT NULL,PRIMARY KEY(user_id,platform),FOREIGN KEY(user_id) REFERENCES users(id));
'''

def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def hash_password(password):
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 240_000)
    return base64.b64encode(digest).decode(), base64.b64encode(salt).decode()

def bootstrap(force=False):
    if not OWNER_PASSWORD:
        raise SystemExit('Set EGM_OWNER_PASSWORD before bootstrap.')
    DATA.mkdir(exist_ok=True)
    if force and DB.exists(): DB.unlink()
    if DB.exists():
        print(f'Database already exists: {DB}')
        return
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA)
    owner_hash, owner_salt = hash_password(OWNER_PASSWORD)
    con.execute('INSERT INTO users VALUES(1,?,?,?,?,"owner","EGM4000 Owner","EGM4000","Administration",?,"active")',
                (OWNER_USERNAME,'owner@egm4000.local',owner_hash,owner_salt,now()))
    generated = []
    session_id = tip_id = 1
    for n in range(1, 238):
        uid = n + 1
        platform = PLATFORMS[(n-1) % len(PLATFORMS)]
        focus = FOCUS[(n-1) % len(FOCUS)]
        username = f'AquaPilot{n:03d}'
        display = f'Aqua Pilot {n:03d}'
        email = f'aquapilot{n:03d}@example.test'
        password = f'EGM!{uid:03d}-' + secrets.token_urlsafe(9)
        ph, salt = hash_password(password)
        joined = (datetime(2026,1,1,tzinfo=timezone.utc)+timedelta(days=n%180)).replace(microsecond=0).isoformat()
        con.execute('INSERT INTO users VALUES(?,?,?,?,?,"user",?,?,?,?,"active")',(uid,username,email,ph,salt,display,platform,focus,joined))
        generated.append([uid,username,password,email,display,platform,focus])
        rng = random.Random(4000+n)
        for j, p in enumerate(PLATFORMS):
            started = (datetime(2026,1,5,tzinfo=timezone.utc)+timedelta(days=(n*3+j*11)%220)).isoformat()
            shots = rng.randint(280,1750); hits = int(shots*rng.uniform(.10,.31)); spend = round(rng.uniform(5,95),2); payout = round(spend*rng.uniform(.55,1.45),2)
            con.execute('INSERT INTO gameplay_sessions VALUES(?,?,?,?,?,?,?,?,?,?,?,"synthetic_seed")',(session_id,uid,p,started,rng.randint(18,95),round(rng.uniform(30,180),2),spend,payout,shots,hits,f'Fictional seed session for {focus}.'))
            evidence=f'{p}: {shots} shots, {hits} hits, spend ${spend:.2f}, return ${payout:.2f}.'
            con.execute('INSERT INTO tips VALUES(?,?,?,?,?,?,?,?)',(tip_id,uid,session_id,started,'Compare multiple sessions','Use repeated evidence rather than one hot or cold run.',evidence,'medium'))
            session_id += 1; tip_id += 1
    for i in range(1,101):
        fid=f'A{i:03d}'; category='Monetization' if 71 <= i <= 95 else 'Administration'
        con.execute('INSERT INTO admin_features VALUES(?,?,?,?)',(fid,f'Admin capability {i:03d}',category,'modelled'))
        con.execute('INSERT INTO checklist VALUES(?,?,0,"")',(fid,f'Admin capability {i:03d}'))
        if 71 <= i <= 95: con.execute('INSERT INTO monetization_channels VALUES(?,?,0,"configuration_required")',(fid,f'Monetization capability {i:03d}'))
    for i in range(1,50):
        rid=f'R{i:03d}'; con.execute('INSERT INTO return_features VALUES(?,?,?)',(rid,f'Return-user feature {i:03d}','modelled')); con.execute('INSERT INTO checklist VALUES(?,?,0,"")',(rid,f'Return-user feature {i:03d}'))
    for i in range(1,13): con.execute('INSERT INTO checklist VALUES(?,?,0,"")',(f'C{i:03d}',f'Core milestone {i:03d}'))
    con.commit(); con.close()
    with CREDS.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(['user_id','username','password','email','display_name','favorite_platform','skill_focus']); w.writerows(generated)
    try: os.chmod(CREDS,0o600)
    except OSError: pass
    print(f'Created {DB}: 1 owner + 237 fictional users, 948 sessions, 948 tips, Admin 100, Monetization 25, Return 49.')
    print(f'Fresh fictional test credentials: {CREDS}')

if __name__ == '__main__':
    import sys
    bootstrap('--force' in sys.argv)
