from __future__ import annotations
import os, sqlite3

DATABASE_URL = os.environ.get('DATABASE_URL','').strip()
POSTGRES = DATABASE_URL.startswith('postgres://') or DATABASE_URL.startswith('postgresql://')

class Cursor:
    def __init__(self, cur, postgres=False):
        self.cur=cur; self.postgres=postgres
    def fetchone(self): return self.cur.fetchone()
    def fetchall(self): return self.cur.fetchall()
    @property
    def lastrowid(self): return getattr(self.cur,'lastrowid',None)

class Connection:
    def __init__(self, raw, postgres=False): self.raw=raw; self.postgres=postgres
    def _sql(self, sql): return sql.replace('?', '%s') if self.postgres else sql
    def execute(self, sql, params=()):
        cur=self.raw.cursor(); cur.execute(self._sql(sql), params); return Cursor(cur,self.postgres)
    def executemany(self, sql, seq):
        cur=self.raw.cursor(); cur.executemany(self._sql(sql),seq); return Cursor(cur,self.postgres)
    def commit(self): self.raw.commit()
    def rollback(self): self.raw.rollback()
    def close(self): self.raw.close()

def connect():
    if POSTGRES:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        raw=psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return Connection(raw,True)
    path=os.environ.get('EGM_SQLITE_PATH')
    if not path:
        from pathlib import Path
        path=str(Path(__file__).resolve().parent/'data'/'egm4000.db')
    raw=sqlite3.connect(path)
    raw.row_factory=sqlite3.Row
    return Connection(raw,False)

def scalar(con, sql, params=()):
    r=con.execute(sql,params).fetchone()
    if r is None: return None
    if isinstance(r,dict): return next(iter(r.values()))
    try: return r[0]
    except Exception: return next(iter(dict(r).values()))

def rowdict(row):
    if row is None: return None
    if isinstance(row,dict): return dict(row)
    return dict(row)

def rowsdict(rows): return [rowdict(r) for r in rows]

def insert_id(con, sql, params=()):
    if con.postgres:
        r=con.execute(sql.rstrip().rstrip(';')+' RETURNING id',params).fetchone()
        return int(r['id'])
    cur=con.execute(sql,params)
    return int(cur.lastrowid)
