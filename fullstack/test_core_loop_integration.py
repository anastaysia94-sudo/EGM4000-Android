#!/usr/bin/env python3
import sqlite3,tempfile,os
from storage import Connection,rowdict
from bootstrap_db import schema_sql,execute_script
from live_intelligence import migrate,start_session,append_event,analyze_session

def main():
    fd,path=tempfile.mkstemp(prefix='egm4000-core-',suffix='.db');os.close(fd)
    try:
        raw=sqlite3.connect(path);raw.row_factory=sqlite3.Row;con=Connection(raw,False)
        execute_script(con,schema_sql(False));con.commit();migrate(con)
        sid=start_session(con,1,'fire-kirin','integration-test')
        events=[
          ('shot_fired','2026-09-06T09:00:00+00:00',0),
          ('shot_fired','2026-09-06T09:00:20+00:00',0),
          ('credit_change','2026-09-06T09:00:30+00:00',-10),
          ('shot_fired','2026-09-06T09:01:00+00:00',0),
          ('shot_fired','2026-09-06T09:01:10+00:00',0),
          ('shot_fired','2026-09-06T09:01:20+00:00',0),
          ('credit_change','2026-09-06T09:01:30+00:00',-20),
          ('break','2026-09-06T09:02:00+00:00',0),
        ]
        for i,(typ,ts,delta) in enumerate(events,1):
            append_event(con,user_id=1,session_id=sid,platform='fire-kirin',event_type=typ,source='integration-test',evidence_type='observed_evidence',confidence=1,payload={'creditDelta':delta},source_event_id=f'test-{i}',event_time=ts)
        a=analyze_session(con,1,sid)
        assert a['schema']=='egm.analysis.v1'
        assert a['metrics']['events']==8
        assert a['metrics']['shots']==5
        assert a['metrics']['credit_delta']==-30
        assert a['quality']['sampleSize']==8
        assert a['coaching']
        tip=rowdict(con.execute('SELECT * FROM tips WHERE user_id=? AND live_session_id=?',(1,sid)).fetchone())
        assert tip is not None
        assert tip['sample_size']==8
        assert tip['evidence_type'] in ('observed_evidence','correlation')
        assert 'random outcome' in tip['uncertainty']
        print('EGM4000 fullstack core loop integration passed')
        con.close()
    finally:
        try:os.unlink(path)
        except OSError:pass
if __name__=='__main__':main()
