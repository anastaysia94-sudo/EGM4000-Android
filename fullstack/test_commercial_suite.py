#!/usr/bin/env python3
"""Contracts for A071/A073/A074/A075/A078/A085/A089."""
from __future__ import annotations
import os,sqlite3,tempfile
from storage import Connection
from commercial_suite import *


def expect(code,fn,kind=ValueError):
    try:fn()
    except kind as exc:assert str(exc)==code,(code,exc)
    else:raise AssertionError(f'expected {code}')


def main():
    fd,path=tempfile.mkstemp(prefix='egm4000-suite-',suffix='.db');os.close(fd)
    try:
        raw=sqlite3.connect(path);raw.row_factory=sqlite3.Row;con=Connection(raw,False)
        con.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,display_name TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'active')")
        con.execute("CREATE TABLE gameplay_sessions(id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,platform TEXT,started_at TEXT,duration_min INTEGER,starting_bankroll REAL,spend REAL,payout REAL,shots INTEGER,hits INTEGER,notes TEXT,source TEXT)")
        for uid,name in [(1,'Owner'),(2,'Pilot Two'),(3,'Coach Three'),(4,'Member Four')]:con.execute("INSERT INTO users(id,display_name,status) VALUES(?,?,'active')",(uid,name))
        con.execute("INSERT INTO gameplay_sessions VALUES(1,2,'Fire Kirin','2026-09-01T00:00:00Z',30,100,20,15,100,20,'recorded','manual')")
        con.execute("INSERT INTO gameplay_sessions VALUES(2,2,'Fire Kirin','2026-09-02T00:00:00Z',45,100,25,30,200,50,'recorded','manual')")
        con.commit();migrate_commercial_suite(con)

        plan=save_plan(con,{'title':'Operator Plus','description':'Evidence tools and collaboration.','price_label':'External billing','features':sorted(FEATURES),'seat_limit':3,'status':'active'})
        assert set(plan['features'])==FEATURES and plan['seatLimit']==3 and plan['status']=='active'
        assert len(public_plans(con)['plans'])==1 and 'does not prove payment' in public_plans(con)['billingBoundary']

        rid=request_plan(con,2,plan['id'],'Need research and team tools')
        assert rid.startswith('pr_')
        expect('plan_request_already_pending',lambda:request_plan(con,2,plan['id']))
        expect('advanced_analytics_entitlement_required',lambda:advanced_analytics(con,2),PermissionError)
        expect('research_lab_entitlement_required',lambda:research_notes(con,2),PermissionError)
        expect('premium_community_entitlement_required',lambda:premium_posts(con,2),PermissionError)
        expect('team_workspace_entitlement_required',lambda:create_workspace(con,2,'No Access Team'),PermissionError)
        expect('unsupported_manual_subscription_source',lambda:grant_subscription(con,2,plan['id'],'provider_verified'))

        sid=grant_subscription(con,2,plan['id'],'external_unverified','External arrangement not provider verified')
        st=my_commercial_status(con,2);assert all(st['features'].values()) and st['subscriptions'][0]['source']=='external_unverified'
        assert st['requests'][0]['status']=='approved' and 'not proof' in st['billingBoundary']

        a=advanced_analytics(con,2);assert a['sessions']==2 and a['shots']==300 and a['hits']==70
        assert abs(a['observedHitRate']-(70/300))<.001 and a['recordedNet']==0.0 and 'do not predict' in a['boundary']

        nid=save_research_note(con,2,{'title':'Pacing hypothesis','body':'Compare observed pace across repeated sessions.','evidence_label':'hypothesis'})
        r=research_notes(con,2);assert r['notes'][0]['id']==nid and r['notes'][0]['user_id']==2 and 'predictions' in r['boundary']
        expect('invalid_evidence_label',lambda:save_research_note(con,2,{'title':'bad','evidence_label':'certainty'}))

        pid=create_premium_post(con,2,{'title':'Evidence review','body':'What repeatable fields are you tracking?'})
        p=premium_posts(con,2);assert p['posts'][0]['id']==pid and p['posts'][0]['display_name']=='Pilot Two' and 'never changes' in p['boundary']

        team=create_workspace(con,2,'Coach Lab','team');add_workspace_member(con,2,team,3,'coach');add_workspace_member(con,2,team,4,'member')
        expect('workspace_seat_limit_reached',lambda:add_workspace_member(con,2,team,1,'member'))
        enterprise=create_workspace(con,2,'Enterprise Evidence Desk','enterprise')
        ws=my_workspaces(con,2);assert {x['id'] for x in ws['workspaces']}=={team,enterprise}
        expect('workspace_not_found',lambda:add_workspace_member(con,3,team,1,'member'))

        owner_sid=grant_subscription(con,1,plan['id'],'complimentary','Owner feature QA')
        f=founder_analytics(con,1);assert f['totals']['activeSubscriptions']==2 and f['totals']['workspaces']==2 and f['totals']['researchNotes']==1 and f['totals']['premiumPosts']==1
        assert 'Revenue is not inferred' in f['boundary']
        snap=admin_commercial_snapshot(con);assert len(snap['plans'])==1 and len(snap['subscriptions'])==2

        revoke_subscription(con,sid);assert my_commercial_status(con,2)['features']['advanced_analytics'] is False
        expect('advanced_analytics_entitlement_required',lambda:advanced_analytics(con,2),PermissionError)
        revoke_subscription(con,owner_sid)
        print('EGM4000 commercial suite passed: plans, analytics, workspaces, research, premium community, enterprise, founder analytics')
        con.close()
    finally:
        try:os.unlink(path)
        except OSError:pass

if __name__=='__main__':main()
