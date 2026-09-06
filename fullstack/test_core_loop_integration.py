#!/usr/bin/env python3
import sqlite3,tempfile,os
from storage import Connection,rowdict
from bootstrap_db import schema_sql,execute_script
from live_intelligence import migrate,start_session,append_event,analyze_session,list_experiments

def add(con,sid,n,prefix,start_min=0):
    for i in range(n):
        minute=start_min+(i//4);second=(i%4)*12
        append_event(con,user_id=1,session_id=sid,platform='fire-kirin',event_type='shot_fired',source='integration-test',evidence_type='observed_evidence',confidence=1,payload={},source_event_id=f'{prefix}-{i}',event_time=f'2026-09-06T09:{minute:02d}:{second:02d}+00:00')

def main():
    fd,path=tempfile.mkstemp(prefix='egm4000-core-',suffix='.db');os.close(fd)
    try:
        raw=sqlite3.connect(path);raw.row_factory=sqlite3.Row;con=Connection(raw,False)
        execute_script(con,schema_sql(False));con.commit();migrate(con)

        # Session A: enough evidence to create a persistent coaching baseline.
        a_sid=start_session(con,1,'fire-kirin','integration-test')
        add(con,a_sid,8,'baseline')
        a=analyze_session(con,1,a_sid)
        assert a['schema']=='egm.analysis.v1'
        assert a['metrics']['events']==8
        assert a['quality']['sampleSize']==8
        tip=rowdict(con.execute('SELECT * FROM tips WHERE user_id=? AND live_session_id=?',(1,a_sid)).fetchone())
        assert tip is not None and tip['sample_size']==8
        experiments=list_experiments(con,1)
        assert len(experiments)==1
        baseline=experiments[0]
        assert baseline['schema']=='egm.coaching-experiment.v1'
        assert baseline['baseline_live_session_id']==a_sid
        assert baseline['target_metric']=='evidence_completeness'
        assert baseline['status']=='waiting_followup'
        assert baseline['result']=='insufficient_evidence'

        # Session B: same platform + enough evidence auto-attaches as follow-up.
        b_sid=start_session(con,1,'fire-kirin','integration-test')
        add(con,b_sid,8,'followup',start_min=10)
        experiments=list_experiments(con,1)
        finished=[x for x in experiments if x['baseline_live_session_id']==a_sid][0]
        assert finished['followup_live_session_id']==b_sid
        assert finished['status']=='completed'
        assert finished['result']=='unchanged'
        assert finished['resultLabel']=='Unchanged'
        assert finished['baseline_sample_size']==8 and finished['followup_sample_size']==8
        assert finished['confidence']>=.45
        assert 'does not prove causation' in finished['uncertainty']

        # Random credit movement may create a review tip, but never a C014 success experiment.
        c_sid=start_session(con,1,'fire-kirin','integration-test')
        append_event(con,user_id=1,session_id=c_sid,platform='fire-kirin',event_type='credit_change',source='integration-test',evidence_type='observed_evidence',confidence=1,payload={'creditDelta':-10},source_event_id='credit-review',event_time='2026-09-06T10:00:00+00:00')
        c_tip=rowdict(con.execute('SELECT * FROM tips WHERE user_id=? AND live_session_id=?',(1,c_sid)).fetchone())
        assert c_tip is not None
        assert con.execute('SELECT id FROM coaching_experiments WHERE tip_id=?',(c_tip['id'],)).fetchone() is None

        print('EGM4000 C006 + C014 core loop integration passed')
        con.close()
    finally:
        try:os.unlink(path)
        except OSError:pass
if __name__=='__main__':main()
