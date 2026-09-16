#!/usr/bin/env python3
"""Credential-safe runtime regression for C003/C007 security operations.

All secrets are generated at runtime and used only against a loopback test server.
No fixed credential or production secret is embedded in this test.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import hmac
import http.cookiejar
import json
import os
from pathlib import Path
import secrets
import shutil
import sqlite3
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parent
PORT=18473
BASE=f'http://127.0.0.1:{PORT}'


def totp(secret):
    padded=secret+'='*((8-len(secret)%8)%8);key=base64.b32decode(padded,casefold=True);counter=int(time.time()//30);msg=struct.pack('>Q',counter);dig=hmac.new(key,msg,hashlib.sha1).digest();off=dig[-1]&15;num=(struct.unpack('>I',dig[off:off+4])[0]&0x7fffffff)%1000000;return f'{num:06d}'


def request(opener,path,method='GET',body=None,csrf=None):
    data=None if body is None else json.dumps(body).encode();req=urllib.request.Request(BASE+path,data=data,method=method)
    if data is not None:req.add_header('Content-Type','application/json')
    if csrf:req.add_header('X-CSRF-Token',csrf)
    try:
        with opener.open(req,timeout=8) as r:return r.status,dict(r.headers),json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        return e.code,dict(e.headers),json.loads(e.read() or b'{}')


def main():
    data=ROOT/'data'
    if data.exists():shutil.rmtree(data)
    owner_password=secrets.token_urlsafe(24);recovery=secrets.token_urlsafe(32);visitor=secrets.token_urlsafe(32);totp_secret='JBSWY3DPEHPK3PXP'
    env=os.environ.copy();env.update({'PORT':str(PORT),'EGM_OWNER_PASSWORD':owner_password,'EGM_OWNER_RECOVERY_TOKEN':recovery,'EGM_VISITOR_SECRET':visitor,'EGM_OWNER_TOTP_SECRET':totp_secret,'EGM_ENV':'test','EGM_SECURE_COOKIES':'0','EGM_TRUST_PROXY':'0'})
    proc=subprocess.Popen([sys.executable,'server.py'],cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    try:
        plain=urllib.request.build_opener()
        for _ in range(80):
            try:
                code,headers,payload=request(plain,'/api/health')
                if code==200:break
            except Exception:pass
            time.sleep(.1)
        else:raise AssertionError('server did not become healthy')
        assert headers.get('X-Frame-Options')=='DENY' and 'frame-ancestors' in headers.get('Content-Security-Policy','')
        code,_,_=request(plain,'/api/admin/features');assert code==401
        code,_,payload=request(plain,'/api/login','POST',{'username':'EGM4000Owner','password':owner_password});assert code==401 and payload['error']=='mfa_required'

        jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        code,_,payload=request(opener,'/api/login','POST',{'username':'EGM4000Owner','password':owner_password,'totp':totp(totp_secret)});assert code==200 and payload['mfa'] is True
        raw_cookie=next(c.value for c in jar if c.name=='egm_session')
        con=sqlite3.connect(data/'egm4000.db');stored=con.execute('SELECT token FROM auth_sessions').fetchone()[0];con.close()
        assert stored==hashlib.sha256(raw_cookie.encode()).hexdigest() and raw_cookie!=stored
        code,_,me=request(opener,'/api/me');assert code==200 and me['authenticated'];csrf=me['csrf']
        code,_,_=request(opener,'/api/admin/run-jobs','POST',{'job_name':'scheduled_blog_publish'});assert code==403
        code,_,payload=request(opener,'/api/admin/run-jobs','POST',{'job_name':'scheduled_blog_publish'},csrf);assert code==200 and payload['ok']
        code,_,payload=request(opener,'/api/admin/create-backup','POST',{},csrf);assert code==201 and payload['ok']
        with gzip.open(payload['path'],'rb') as f:backup=json.loads(f.read())
        user_rows=backup['tables']['users'];assert user_rows and all('password_hash' not in x and 'salt' not in x for x in user_rows)
        assert 'auth_sessions' not in backup['tables'] and 'mobile_tokens' not in backup['tables']

        code,_,_=request(plain,'/api/owner/recover','POST',{'recovery_token':'wrong-'+secrets.token_hex(4),'new_password':secrets.token_urlsafe(24)});assert code==403
        new_password=secrets.token_urlsafe(24)
        code,_,payload=request(plain,'/api/owner/recover','POST',{'recovery_token':recovery,'new_password':new_password});assert code==200 and payload['sessions_invalidated']
        code,_,me=request(opener,'/api/me');assert code==200 and me['authenticated'] is False

        jar2=http.cookiejar.CookieJar();opener2=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar2))
        code,_,_=request(opener2,'/api/login','POST',{'username':'EGM4000Owner','password':new_password,'totp':totp(totp_secret)});assert code==200
        code,_,_=request(opener2,'/api/logout','POST',{});assert code==200
        code,_,me=request(opener2,'/api/me');assert me['authenticated'] is False
        print('C003/C007 runtime security operations verified')
    finally:
        proc.terminate()
        try:proc.wait(timeout=5)
        except subprocess.TimeoutExpired:proc.kill()
        if data.exists():shutil.rmtree(data)

if __name__=='__main__':main()
