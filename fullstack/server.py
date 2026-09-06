#!/usr/bin/env python3
"""EGM4000 database-backed reference server (standard library only)."""
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime, timedelta, timezone
from http.cookies import SimpleCookie
import base64, hashlib, hmac, json, mimetypes, os, secrets, sqlite3
from bootstrap_db import bootstrap
from live_intelligence import ADAPTERS, append_event, metrics, migrate, start_session, context_pack

ROOT=Path(__file__).resolve().parent; STATIC=ROOT/'static'; DB=ROOT/'data'/'egm4000.db'
HOST=os.environ.get('EGM_HOST','127.0.0.1'); PORT=int(os.environ.get('EGM_PORT','8040'))
if not DB.exists(): bootstrap()
con=sqlite3.connect(DB); migrate(con); con.close()
def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def db(): c=sqlite3.connect(DB); c.row_factory=sqlite3.Row; return c
def verify(password,stored,salt):
    raw=base64.b64decode(salt); d=hashlib.pbkdf2_hmac('sha256',password.encode(),raw,240_000); return hmac.compare_digest(base64.b64encode(d).decode(),stored)

class App(BaseHTTPRequestHandler):
    server_version='EGM4000/1.1'
    def log_message(self,fmt,*args): print('[EGM4000]',fmt%args)
    def body(self):
        try:return json.loads(self.rfile.read(int(self.headers.get('Content-Length','0') or 0)) or b'{}')
        except:return {}
    def json(self,obj,status=200,cookies=None):
        b=json.dumps(obj).encode(); self.send_response(status); self.send_header('Content-Type','application/json'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(b)))
        for c in cookies or []: self.send_header('Set-Cookie',c)
        self.end_headers(); self.wfile.write(b)
    def session(self):
        c=SimpleCookie(); c.load(self.headers.get('Cookie','')); item=c.get('egm_session')
        if not item:return None
        con=db(); r=con.execute('SELECT s.token,s.csrf,s.expires_at,u.* FROM auth_sessions s JOIN users u ON u.id=s.user_id WHERE s.token=?',(item.value,)).fetchone(); con.close()
        return dict(r) if r and r['expires_at']>now() and r['status']=='active' else None
    def need(self,owner=False,csrf=False):
        s=self.session()
        if not s:self.json({'error':'authentication_required'},401); return None
        if owner and s['role']!='owner':self.json({'error':'owner_only'},403); return None
        if csrf and self.headers.get('X-CSRF-Token')!=s['csrf']:self.json({'error':'csrf_failed'},403); return None
        return s
    def do_GET(self):
        p=urlparse(self.path); path=p.path
        if path=='/api/health': return self.json({'ok':True,'service':'EGM4000 fullstack','schema':'egm.event.v1'})
        if path=='/api/adapters': return self.json(list(ADAPTERS))
        if path=='/api/me':
            s=self.session(); return self.json({'authenticated':False} if not s else {'authenticated':True,'user':{k:s[k] for k in ['id','username','display_name','role','favorite_platform','skill_focus']},'csrf':s['csrf']})
        if path=='/api/summary':
            s=self.need();
            if not s:return
            con=db(); counts={t:con.execute(f'SELECT COUNT(*) FROM {t} WHERE user_id=?',(s['id'],)).fetchone()[0] for t in ['gameplay_sessions','tips']}; con.close(); return self.json(counts)
        if path=='/api/live/replay':
            s=self.need();
            if not s:return
            con=db(); rows=con.execute('SELECT * FROM normalized_events WHERE user_id=? ORDER BY id DESC LIMIT 300',(s['id'],)).fetchall(); con.close(); return self.json([dict(r) for r in rows])
        if path=='/api/live/context':
            s=self.need();
            if not s:return
            con=db(); out=context_pack(con,s['id']); con.close(); return self.json(out)
        if path=='/api/admin/counts':
            s=self.need(owner=True);
            if not s:return
            con=db(); out={t:con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for t in ['users','gameplay_sessions','tips','admin_features','monetization_channels','return_features','checklist']}; con.close(); return self.json(out)
        return self.serve(path)
    def do_POST(self):
        path=urlparse(self.path).path; b=self.body()
        if path=='/api/login':
            con=db(); u=con.execute('SELECT * FROM users WHERE username=?',(str(b.get('username','')),)).fetchone()
            if not u or not verify(str(b.get('password','')),u['password_hash'],u['salt']): con.close(); return self.json({'error':'invalid_credentials'},401)
            tok=secrets.token_urlsafe(32); csrf=secrets.token_urlsafe(24); exp=(datetime.now(timezone.utc)+timedelta(hours=12)).replace(microsecond=0).isoformat(); con.execute('INSERT INTO auth_sessions VALUES(?,?,?,?,?)',(tok,u['id'],csrf,now(),exp)); con.commit(); con.close(); return self.json({'ok':True},cookies=[f'egm_session={tok}; Path=/; HttpOnly; SameSite=Lax; Max-Age=43200'])
        if path=='/api/logout':
            s=self.session();
            if s:
                con=db(); con.execute('DELETE FROM auth_sessions WHERE token=?',(s['token'],)); con.commit(); con.close()
            return self.json({'ok':True},cookies=['egm_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax'])
        if path=='/api/live/start':
            s=self.need(csrf=True);
            if not s:return
            platform=str(b.get('platform','generic'))[:60]; con=db(); sid=start_session(con,s['id'],platform); con.close(); return self.json({'ok':True,'session_id':sid,'platform':platform})
        if path=='/api/live/event':
            s=self.need(csrf=True);
            if not s:return
            sid=int(b.get('session_id',0)); evidence=str(b.get('evidence_type','observed_evidence')); source='user-verified' if evidence=='observed_evidence' else 'vision-estimate'; con=db()
            try:eid=append_event(con,user_id=s['id'],session_id=sid,platform=str(b.get('platform','generic')),event_type=str(b.get('type','annotation'))[:80],source=source,evidence_type=evidence,confidence=float(b.get('confidence',1)),payload=b.get('payload') if isinstance(b.get('payload'),dict) else {})
            except Exception as e: con.close(); return self.json({'error':str(e)},400)
            out=metrics(con,s['id'],sid); con.close(); return self.json({'ok':True,'event_id':eid,'metrics':out})
        return self.json({'error':'not_found'},404)
    def serve(self,path):
        rel='index.html' if path=='/' else path.lstrip('/'); fp=(STATIC/rel).resolve()
        if not str(fp).startswith(str(STATIC.resolve())) or not fp.exists(): fp=STATIC/'index.html'
        data=fp.read_bytes(); self.send_response(200); self.send_header('Content-Type',mimetypes.guess_type(str(fp))[0] or 'application/octet-stream'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)

if __name__=='__main__':
    print(f'EGM4000 fullstack: http://{HOST}:{PORT}')
    ThreadingHTTPServer((HOST,PORT),App).serve_forever()
