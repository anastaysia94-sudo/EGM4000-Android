from __future__ import annotations
import os, re, sqlite3

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

def _sync_postgres_serial_sequence(con, sql):
    """Keep SERIAL ids ahead of explicit seed ids before public inserts.

    EGM4000 intentionally seeds deterministic ids for users/community fixtures. PostgreSQL
    sequences do not automatically advance when an explicit id is inserted, so the first
    later INSERT could otherwise collide with an existing seed row. This helper derives the
    trusted table name from the application's INSERT statement and advances that table's
    serial sequence to MAX(id) immediately before auto-id insertion.
    """
    match=re.match(r'\s*INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)',sql,re.IGNORECASE)
    if not match:return
    table=match.group(1)
    seq=scalar(con,"SELECT pg_get_serial_sequence(?, 'id')",(table,))
    if not seq:return
    max_id=scalar(con,f'SELECT MAX(id) FROM {table}')
    if max_id is None:
        con.execute('SELECT setval(?::regclass,1,false)',(seq,))
    else:
        con.execute('SELECT setval(?::regclass,?,true)',(seq,int(max_id)))

def insert_id(con, sql, params=()):
    if con.postgres:
        _sync_postgres_serial_sequence(con,sql)
        r=con.execute(sql.rstrip().rstrip(';')+' RETURNING id',params).fetchone()
        return int(r['id'])
    cur=con.execute(sql,params)
    return int(cur.lastrowid)
