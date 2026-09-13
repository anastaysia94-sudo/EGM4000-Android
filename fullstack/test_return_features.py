#!/usr/bin/env python3
"""C009 registry + completed Return User Lab contract checks."""
from datetime import datetime, timezone
import os,sqlite3,tempfile
from storage import Connection
from bootstrap_db import schema_sql,execute_script
from return_registry import TITLES,IMPLEMENTED,sync_return_registry
from return_workspace import build_return_workspace,migrate_return_workspace

def main():
    fd,path=tempfile.mkstemp(prefix='egm4000-return-',suffix='.db');os.close(fd)
    try:
        raw=sqlite3.connect(path);raw.row_factory=sqlite3.Row;con=Connection(raw,False)
        execute_script(con,schema_sql(False));con.commit()
        sync_return_registry(con);migrate_return_workspace(con)
        rows=con.execute('SELECT id,title,implementation_status FROM return_features ORDER BY id').fetchall()
        assert len(TITLES)==49 and len(rows)==49
        assert rows[0]['id']=='R001' and rows[0]['title']=='Today dashboard'
        assert rows[-1]['id']=='R049' and rows[-1]['title']=='Monthly personal report'
        assert sum(r['implementation_status']=='implemented' for r in rows)==len(IMPLEMENTED)==49
        assert sum(r['implementation_status']=='modelled' for r in rows)==0
        assert con.execute("SELECT COUNT(*) FROM checklist WHERE id LIKE 'R%' AND done=1").fetchone()[0]==49

        stamp=datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        con.execute("INSERT INTO users(id,username,email,password_hash,salt,role,display_name,joined_at,status,is_synthetic) VALUES(1,'tester','tester@example.test','x','x','user','Tester',?,'active',0)",(stamp,))
        con.execute("INSERT INTO gameplay_sessions(id,user_id,platform,started_at,duration_min,spend,payout,shots,hits,notes,source) VALUES(1,1,'Fire Kirin',?,75,20,18,100,25,'test','manual')",(stamp,))
        con.execute("INSERT INTO tips(id,user_id,session_id,created_at,title,body,evidence,confidence) VALUES(1,1,1,?,'Slow the pace','Compare repeated evidence.','test','medium')",(stamp,))
        con.execute("INSERT INTO live_sessions(id,user_id,platform,started_at,status,source,created_at) VALUES(1,1,'Fire Kirin',?,'ended','authorized_capture',?)",(stamp,stamp))
        con.execute("INSERT INTO normalized_events(id,live_session_id,user_id,source_event_id,event_time,platform,event_type,source,evidence_type,confidence,payload_json,created_at) VALUES(1,1,1,'e1',?,'Fire Kirin','shot_fired','manual','observed_evidence',1,'{\"target\":\"clownfish\",\"weapon\":\"level-5\",\"denomination\":\"10\",\"cost\":0.1}',?)",(stamp,stamp))
        con.execute("INSERT INTO normalized_events(id,live_session_id,user_id,source_event_id,event_time,platform,event_type,source,evidence_type,confidence,payload_json,created_at) VALUES(2,1,1,'e2',?,'Fire Kirin','target_hit','manual','observed_evidence',1,'{\"target\":\"clownfish\",\"weapon\":\"level-5\",\"denomination\":\"10\",\"hit\":true}',?)",(stamp,stamp))
        con.execute("INSERT INTO return_tip_feedback(user_id,tip_id,rating,note,updated_at) VALUES(1,1,5,'Useful',?)",(stamp,))
        con.execute("INSERT INTO return_goals(id,user_id,goal_type,target,title,status,created_at,updated_at) VALUES('g1',1,'tip_reviews',3,'Review coaching evidence','active',?,?)",(stamp,stamp))
        con.execute("INSERT INTO return_preferences(user_id,notifications_enabled,tip_notifications,review_notifications,pause_until,updated_at) VALUES(1,1,1,1,'',?)",(stamp,))
        con.execute("INSERT INTO return_notes(id,user_id,note_type,body,tags_json,created_at) VALUES('n1',1,'reflection','Review pacing and breaks','[\"evidence\",\"pacing\",\"breaks\"]',?)",(stamp,))
        con.execute("INSERT INTO return_saved_views(id,user_id,title,config_json,created_at,updated_at) VALUES('v1',1,'Evening review','{\"surface\":\"return_lab\"}',?,?)",(stamp,stamp))
        con.commit()

        w=build_return_workspace(con,1)
        assert w['schema']=='egm.return-workspace.v1'
        assert w['personalBest']['hitRate']==0.25
        assert w['targetEfficiency'] and w['targetEfficiency'][0]['name']=='clownfish'
        assert w['weaponEfficiency'] and w['weaponEfficiency'][0]['name']=='level-5'
        assert w['denominationComparison'] and w['denominationComparison'][0]['name']=='10'
        assert w['timeAnalysis']
        assert w['fatigueWarning']['active'] is True
        assert w['coachInbox'][0]['rating']==5
        assert w['goals'][0]['current']==1 and w['goals'][0]['target']==3
        assert w['notes'] and w['savedViews']
        print('EGM4000 C009 passed: 49/49 implemented + Return User Lab analytics/persistence')
        con.close()
    finally:
        try:os.unlink(path)
        except OSError:pass

if __name__=='__main__':main()
