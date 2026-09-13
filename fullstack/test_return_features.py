#!/usr/bin/env python3
"""C009 registry and dashboard/adoption contract checks."""
import sqlite3,tempfile,os
from storage import Connection
from bootstrap_db import schema_sql,execute_script
from return_registry import TITLES,IMPLEMENTED,sync_return_registry

def main():
    fd,path=tempfile.mkstemp(prefix='egm4000-return-',suffix='.db');os.close(fd)
    try:
        raw=sqlite3.connect(path);raw.row_factory=sqlite3.Row;con=Connection(raw,False)
        execute_script(con,schema_sql(False));con.commit()
        sync_return_registry(con)
        rows=con.execute('SELECT id,title,implementation_status FROM return_features ORDER BY id').fetchall()
        assert len(TITLES)==49 and len(rows)==49
        assert rows[0]['id']=='R001' and rows[0]['title']=='Today dashboard'
        assert rows[-1]['id']=='R049' and rows[-1]['title']=='Monthly personal report'
        assert sum(r['implementation_status']=='implemented' for r in rows)==len(IMPLEMENTED)==30
        assert sum(r['implementation_status']=='modelled' for r in rows)==19
        assert con.execute("SELECT COUNT(*) FROM checklist WHERE id LIKE 'R%' AND done=1").fetchone()[0]==30
        print('EGM4000 C009 return registry passed: 49 named / 30 implemented / 19 modelled')
        con.close()
    finally:
        try:os.unlink(path)
        except OSError:pass
if __name__=='__main__':main()
