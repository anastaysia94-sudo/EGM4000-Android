#!/usr/bin/env python3
"""Live HTTP smoke for A084 without login/password fixtures.

The test prebuilds a temporary database with a non-authenticated fixture user so
server bootstrap preserves it instead of requiring owner credential seeding. It
then provisions ephemeral API clients directly through the A084 engine and tests
the public aggregate developer endpoints over HTTP.
"""
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from bootstrap_db import ensure_schema
from commercial_access import migrate_commercial_access, save_api_client
from storage import Connection

ROOT=Path(__file__).resolve().parent
PORT=8051
BASE=f"http://127.0.0.1:{PORT}"


def request(path,key=None):
    headers={}
    if key:headers['X-EGM-API-Key']=key
    req=Request(BASE+path,headers=headers,method='GET')
    try:
        with urlopen(req,timeout=3) as resp:
            return resp.status,json.loads(resp.read().decode())
    except HTTPError as exc:
        return exc.code,json.loads(exc.read().decode())


def wait_ready(proc):
    for _ in range(40):
        if proc.poll() is not None:
            raise AssertionError(f'server exited early with {proc.returncode}')
        try:
            status,payload=request('/api/health')
            if status==200 and payload.get('schema')=='egm.event.v1':return
        except (URLError,TimeoutError,ConnectionError):pass
        time.sleep(.25)
    raise AssertionError('A084 test server did not become ready')


def main():
    fd,path=tempfile.mkstemp(prefix='egm4000-a084-http-',suffix='.db');os.close(fd)
    log=tempfile.NamedTemporaryFile(prefix='egm4000-a084-',suffix='.log',delete=False);log_path=log.name;log.close()
    proc=None
    try:
        raw=sqlite3.connect(path);raw.row_factory=sqlite3.Row;con=Connection(raw,False)
        ensure_schema(con)
        con.execute("""INSERT INTO users(id,username,email,password_hash,salt,role,display_name,bio,joined_at,status,is_synthetic)
                       VALUES(1,'fixture_owner','fixture-owner@example.test','unused','unused','owner','Fixture Owner','A084 HTTP fixture','2026-09-16T00:00:00+00:00','active',1)""")
        con.execute("""INSERT INTO gameplay_sessions(id,user_id,platform,started_at,duration_min,spend,payout,shots,hits,source)
                       VALUES(1,1,'Fire Kirin','2026-09-01T00:00:00+00:00',20,10,9,100,20,'fixture'),
                             (2,1,'Juwa','2026-09-02T00:00:00+00:00',25,12,11,120,25,'fixture')""")
        con.execute("""INSERT INTO live_sessions(id,user_id,platform,started_at,status,source,created_at)
                       VALUES(1,1,'Fire Kirin','2026-09-03T00:00:00+00:00','ended','authorized_capture','2026-09-03T00:00:00+00:00')""")
        con.execute("""INSERT INTO normalized_events(id,live_session_id,user_id,event_time,platform,event_type,source,evidence_type,confidence,payload_json,created_at)
                       VALUES(1,1,1,'2026-09-03T00:01:00+00:00','Fire Kirin','shot_fired','fixture','observed_evidence',0.9,'{}','2026-09-03T00:01:00+00:00'),
                             (2,1,1,'2026-09-03T00:02:00+00:00','Fire Kirin','hit','fixture','observed_evidence',0.9,'{}','2026-09-03T00:02:00+00:00')""")
        migrate_commercial_access(con)
        summary=save_api_client(con,{'name':'HTTP summary fixture','plan':'developer','scopes':['summary'],'daily_quota':1,'active':True});summary_key=summary['apiKey']
        evidence=save_api_client(con,{'name':'HTTP evidence fixture','plan':'developer','scopes':['evidence'],'daily_quota':2,'active':True});evidence_key=evidence['apiKey']
        stored=con.execute("SELECT key_hash FROM api_access_clients WHERE id=?",(summary['id'],)).fetchone()['key_hash'];assert summary_key not in stored
        con.close()

        env=os.environ.copy();env.update({'EGM_SQLITE_PATH':path,'EGM_PORT':str(PORT),'EGM_HOST':'127.0.0.1','EGM_SECURE_COOKIES':'0'})
        with open(log_path,'w',encoding='utf-8') as out:
            proc=subprocess.Popen([sys.executable,'server.py'],cwd=ROOT,env=env,stdout=out,stderr=subprocess.STDOUT)
        wait_ready(proc)

        status,payload=request('/api/developer/platform-summary');assert status==401 and payload['error']=='api_key_required'
        status,payload=request('/api/developer/platform-summary','not-a-real-key');assert status==401 and payload['error']=='invalid_api_key'
        status,payload=request('/api/developer/platform-summary',summary_key);assert status==200
        assert payload['historicalSessions'][0]['session_count']>=1 and payload['usage']['usedToday']==1 and payload['usage']['remainingToday']==0
        assert 'Aggregate session counts only' in payload['privacy']
        status,payload=request('/api/developer/evidence-summary',summary_key);assert status==403 and payload['error']=='api_scope_denied'
        status,payload=request('/api/developer/platform-summary',summary_key);assert status==429 and payload['error']=='api_daily_quota_exceeded'
        status,payload=request('/api/developer/evidence-summary',evidence_key);assert status==200
        assert payload['evidence'][0]['event_count']==2 and 'do not expose credentials' in payload['boundary']
        assert payload['usage']['usedToday']==1 and payload['usage']['remainingToday']==1
        print('EGM4000 A084 HTTP passed: aggregate-only API, hashed keys, scopes, quota and safe errors')
    finally:
        if proc and proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=3)
            except subprocess.TimeoutExpired:proc.kill()
        for p in (path,log_path):
            try:os.unlink(p)
            except OSError:pass

if __name__=='__main__':main()
