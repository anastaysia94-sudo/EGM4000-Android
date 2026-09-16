#!/usr/bin/env python3
import sqlite3

from coaching_trends import migrate_coaching_trends, owner_overview, user_trends


def db():
    con=sqlite3.connect(':memory:');con.row_factory=sqlite3.Row
    con.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,status TEXT NOT NULL,is_synthetic INTEGER NOT NULL DEFAULT 0)")
    con.execute("CREATE TABLE checklist(id TEXT PRIMARY KEY,title TEXT NOT NULL,done INTEGER NOT NULL DEFAULT 0,notes TEXT NOT NULL DEFAULT '')")
    con.execute("""CREATE TABLE coaching_experiments(
      id INTEGER PRIMARY KEY,user_id INTEGER NOT NULL,baseline_live_session_id INTEGER NOT NULL,followup_live_session_id INTEGER,
      platform TEXT NOT NULL,target_metric TEXT NOT NULL,status TEXT NOT NULL,result TEXT NOT NULL,confidence REAL NOT NULL,
      baseline_sample_size INTEGER NOT NULL,followup_sample_size INTEGER NOT NULL,updated_at TEXT NOT NULL
    )""")
    con.execute("INSERT INTO users VALUES(1,'active',0)")
    con.execute("INSERT INTO users VALUES(2,'active',1)")
    return con


def add(con,idx,user,result,metric='shots_per_min',confidence=.8,platform='fire-kirin',base_n=20,follow_n=20):
    con.execute("INSERT INTO coaching_experiments VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(
        idx,user,idx*2,idx*2+1,platform,metric,'completed',result,confidence,base_n,follow_n,f'2026-09-16T00:{idx:02d}:00+00:00'))


def main():
    con=db();migrate_coaching_trends(con)
    c=con.execute("SELECT done,notes FROM checklist WHERE id='C016'").fetchone();assert c['done']==1 and 'random outcomes excluded' in c['notes']

    add(con,1,1,'improved');add(con,2,1,'improved');add(con,3,1,'unchanged')
    t=user_trends(con,1);g=t['groups'][0]
    assert t['schema']=='egm.coaching-trends.v1'
    assert g['classification']=='improving_pattern' and g['completedComparisons']==3
    assert g['sessionCount']==6 and 0<g['confidence']<=1
    assert 'causal' in t['boundary'] and 'random credit' in t['boundary']

    add(con,4,1,'worsened',metric='breaks');add(con,5,1,'improved',metric='breaks')
    insufficient=[x for x in user_trends(con,1)['groups'] if x['targetMetric']=='breaks'][0]
    assert insufficient['classification']=='insufficient_evidence'

    add(con,6,1,'worsened',metric='max_drawdown');add(con,7,1,'worsened',metric='max_drawdown');add(con,8,1,'unchanged',metric='max_drawdown')
    worsening=[x for x in user_trends(con,1)['groups'] if x['targetMetric']=='max_drawdown'][0]
    assert worsening['classification']=='worsening_pattern'

    add(con,9,1,'improved',metric='evidence_completeness');add(con,10,1,'worsened',metric='evidence_completeness');add(con,11,1,'unchanged',metric='evidence_completeness')
    mixed=[x for x in user_trends(con,1)['groups'] if x['targetMetric']=='evidence_completeness'][0]
    assert mixed['classification']=='mixed_or_stable'

    # Synthetic data must not become owner adoption/trend evidence.
    add(con,12,2,'improved');add(con,13,2,'improved');add(con,14,2,'improved')
    o=owner_overview(con)
    assert o['eligibleRealUsers']==1 and o['measuredRealUsers']==1
    assert o['completedComparisons']==11
    assert all('payout' not in str(x).lower() and 'profit' not in str(x).lower() for x in o['groups'])
    con.close();print('C016 coaching trends verified')

if __name__=='__main__':main()
