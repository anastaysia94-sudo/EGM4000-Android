#!/usr/bin/env python3
import sqlite3,tempfile,os
from storage import Connection,rowdict
from bootstrap_db import schema_sql,execute_script
from live_intelligence import migrate,start_session,append_event,analyze_session,list_experiments

def event(con,sid,event_type,event_id,stamp):
    append_event(con,user_id=1,session_id=sid,platform='fire-kirin',event_type=event_type,source='integration-test',evidence_type='observed_evidence',confidence=1,payload={},source_event_id=event_id,event_time=stamp)

def main():
    fd,path=tempfile.mkstemp(prefix='egm4000-core-',suffix='.db');os.close(fd)
    try:
        raw=sqlite3.connect(path);raw.row_factory=sqlite3.Row;con=Connection(raw,False)
        execute_script(con,schema_sql(False));con.commit();migrate(con)

        # Session A begins with generic evidence coaching, then matures into a
        # specific no-break recommendation as the same baseline reaches 30+ min.
        a_sid=start_session(con,1,'fire-kirin','integration-test')
        baseline_times=['09:00:00','09:04:00','09:08:00','09:12:00','09:16:00','09:20:00','09:24:00','09:31:00']
        for i,t in enumerate(baseline_times):event(con,a_sid,'shot_fired',f'baseline-{i}',f'2026-09-06T{t}+00:00')
        a=analyze_session(con,1,a_sid)
        assert a['schema']=='egm.analysis.v1'
        assert a['metrics']['events']==8 and a['metrics']['breaks']==0
        assert a['quality']['sampleSize']==8
        assert a['coaching'][0]['targetMetric']=='breaks'
        tip=rowdict(con.execute('SELECT * FROM tips WHERE user_id=? AND live_session_id=?',(1,a_sid)).fetchone())
        assert tip is not None and tip['sample_size']==8
        experiments=list_experiments(con,1)
        assert len(experiments)==1
        baseline=experiments[0]
        assert baseline['schema']=='egm.coaching-experiment.v1'
        assert baseline['baseline_live_session_id']==a_sid
        assert baseline['target_metric']=='breaks'  # proves pending target upgraded from generic evidence completeness
        assert baseline['baseline_value']==0
        assert baseline['status']=='waiting_followup'
        assert baseline['result']=='insufficient_evidence'

        # Session B records a break. At 8 comparable evidence points, C014
        # automatically attaches it and classifies the behavior metric as Improved.
        b_sid=start_session(con,1,'fire-kirin','integration-test')
        follow_types=['shot_fired','shot_fired','break','shot_fired','shot_fired','shot_fired','shot_fired','shot_fired']
        for i,typ in enumerate(follow_types):event(con,b_sid,typ,f'followup-{i}',f'2026-09-06T10:{i:02d}:00+00:00')
        experiments=list_experiments(con,1)
        finished=[x for x in experiments if x['baseline_live_session_id']==a_sid][0]
        assert finished['followup_live_session_id']==b_sid
        assert finished['status']=='completed'
        assert finished['target_metric']=='breaks'
        assert finished['followup_value']==1
        assert finished['result']=='improved'
        assert finished['resultLabel']=='Improved'
        assert finished['baseline_sample_size']==8 and finished['followup_sample_size']==8
        assert finished['confidence']>=.45
        assert 'does not prove causation' in finished['uncertainty']

        # Random credit movement can create a review tip, but it cannot create
        # a C014 success experiment or claim a random result was improved.
        c_sid=start_session(con,1,'fire-kirin','integration-test')
        append_event(con,user_id=1,session_id=c_sid,platform='fire-kirin',event_type='credit_change',source='integration-test',evidence_type='observed_evidence',confidence=1,payload={'creditDelta':-10},source_event_id='credit-review',event_time='2026-09-06T11:00:00+00:00')
        c_tip=rowdict(con.execute('SELECT * FROM tips WHERE user_id=? AND live_session_id=?',(1,c_sid)).fetchone())
        assert c_tip is not None
        assert con.execute('SELECT id FROM coaching_experiments WHERE tip_id=?',(c_tip['id'],)).fetchone() is None

        print('EGM4000 C006 + C014 behavior comparison integration passed')
        con.close()
    finally:
        try:os.unlink(path)
        except OSError:pass
if __name__=='__main__':main()
