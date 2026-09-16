#!/usr/bin/env python3
"""Contracts for A072/A086/A088/A094/A095."""
from __future__ import annotations
from datetime import datetime,timedelta,timezone
import json,os,sqlite3,tempfile
from storage import Connection
from commercial_suite import migrate_commercial_suite,save_plan,my_commercial_status
from billing_controls import *


def expect(code,fn,kind=ValueError):
    try:fn()
    except kind as exc:assert str(exc)==code,(code,exc)
    else:raise AssertionError(f'expected {code}')


def event(event_id,provider,customer,event_type,**extra):
    payload={'event_id':event_id,'provider':provider,'customer_ref':customer,'event_type':event_type,'status':'active' if event_type.endswith('_active') else 'cancelled','occurred_at':_now()}
    payload.update(extra);return json.dumps(payload,separators=(',',':')).encode()


def main():
    fd,path=tempfile.mkstemp(prefix='egm4000-billing-',suffix='.db');os.close(fd)
    try:
        raw=sqlite3.connect(path);raw.row_factory=sqlite3.Row;con=Connection(raw,False)
        con.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT,display_name TEXT,status TEXT NOT NULL DEFAULT 'active')")
        con.execute("CREATE TABLE gameplay_sessions(id INTEGER PRIMARY KEY,user_id INTEGER,platform TEXT,started_at TEXT,duration_min INTEGER,starting_bankroll REAL,spend REAL,payout REAL,shots INTEGER,hits INTEGER,notes TEXT,source TEXT)")
        con.execute("CREATE TABLE tips(id INTEGER PRIMARY KEY,user_id INTEGER,session_id INTEGER,created_at TEXT,title TEXT,body TEXT,evidence TEXT,confidence TEXT)")
        con.execute("CREATE TABLE feature_usage_events(id INTEGER PRIMARY KEY,user_id INTEGER,feature_id TEXT,event_name TEXT,context_json TEXT,created_at TEXT)")
        for uid in (1,2,3):con.execute("INSERT INTO users VALUES(?,?,?,'active')",(uid,f'u{uid}',f'User {uid}'))
        con.execute("INSERT INTO gameplay_sessions VALUES(1,2,'Fire Kirin','2026-09-01T00:00:00+00:00',30,100,20,15,100,20,'owned','manual')")
        con.execute("INSERT INTO gameplay_sessions VALUES(2,2,'Fire Kirin','2026-09-05T00:00:00+00:00',25,100,10,12,80,16,'owned','manual')")
        con.execute("INSERT INTO tips VALUES(1,2,1,'2026-09-01T00:10:00+00:00','Review pacing','Compare repeated evidence.','Observed pace increased.','medium')")
        con.execute("INSERT INTO tips VALUES(2,2,2,'2026-09-05T00:10:00+00:00','Take a break','Long sessions can reduce evidence quality.','Observed duration.','medium')")
        con.execute("INSERT INTO feature_usage_events VALUES(1,2,'R001','open','{}','2026-09-10T00:00:00+00:00')")
        con.commit();migrate_commercial_suite(con);migrate_billing_controls(con)

        plan=save_plan(con,{'title':'Verified Plan','features':['advanced_analytics'],'status':'active'})
        expect('unsupported_manual_addon_source',lambda:grant_addon(con,2,A072,'provider_verified',limit_value=5))

        grant_addon(con,2,A072,'external_unverified',limit_value=2,note='External arrangement not provider verified')
        first=consume_coaching(con,2,'first digest');second=consume_coaching(con,2,'second digest')
        assert first['status']['remainingUnits']==1 and second['status']['remainingUnits']==0
        assert len(first['tips'])==2 and 'does not improve random odds' in first['boundary']
        expect('usage_coaching_limit_reached',lambda:consume_coaching(con,2),PermissionError)

        grant_addon(con,2,A086,'complimentary',note='QA')
        ri=retention_insights(con,2);assert ri['activeDays']==3 and ri['longestObservedGapDays']==5 and 'do not predict' in ri['boundary']

        grant_addon(con,2,A088,'complimentary',retain_days=30,note='QA')
        arc=create_retention_archive(con,2);assert arc['rowCount']==4 and arc['retainDays']==30
        owned=get_retention_archive(con,2,arc['id']);payload=json.loads(owned['content']);assert payload['userId']==2 and len(payload['sessions'])==2 and len(payload['tips'])==2
        text=owned['content'].lower();assert 'password' not in text and 'auth_sessions' not in text and 'visitor' not in text
        expect('retention_archive_not_found',lambda:get_retention_archive(con,3,arc['id']))
        future=(datetime.now(timezone.utc)+timedelta(days=31)).replace(microsecond=0).isoformat();assert prune_expired_archives(con,future)==1

        save_coupon(con,{'code':'TRYPLAN','title':'7 day plan trial','kind':'trial_plan','target_plan_id':plan['id'],'trial_days':7,'max_redemptions':10})
        trial=redeem_coupon(con,2,'tryplan');assert trial['kind']=='trial_plan' and trial['status']=='applied' and trial['subscriptionId']
        assert my_commercial_status(con,2)['subscriptions'][0]['source']=='complimentary'
        expect('coupon_already_redeemed',lambda:redeem_coupon(con,2,'TRYPLAN'))

        save_coupon(con,{'code':'COACH5','title':'Five coaching units','kind':'coaching_units','unit_bonus':5,'max_redemptions':1})
        units=redeem_coupon(con,3,'COACH5');assert units['access']['limitValue']==5 and units['access']['source']=='complimentary'
        save_coupon(con,{'code':'SAVE20','title':'Discount reservation','kind':'discount','discount_label':'20% off verified checkout','max_redemptions':10})
        disc=redeem_coupon(con,3,'SAVE20');assert disc['status']=='reserved' and 'grants no paid access' in disc['billingBoundary']

        save_customer_link(con,'testpay','cust-plan',3,'plan',plan['id'])
        secret='unit-test-signing-key-not-a-production-secret'
        raw_event=event('evt-plan-1','testpay','cust-plan','plan_active',amount='19.00',currency='usd')
        sig=expected_signature(raw_event,secret)
        expect('billing_signature_invalid',lambda:ingest_signed_provider_event(con,raw_event,'sha256=bad',secret),PermissionError)
        reconciled=ingest_signed_provider_event(con,raw_event,sig,secret);assert reconciled['reconciliationStatus']=='reconciled'
        duplicate=ingest_signed_provider_event(con,raw_event,sig,secret);assert duplicate['duplicate'] is True
        sub=con.execute("SELECT * FROM commercial_subscriptions WHERE user_id=3 AND plan_id=? ORDER BY updated_at DESC LIMIT 1",(plan['id'],)).fetchone();assert sub['source']=='provider_verified' and sub['source_ref']=='evt-plan-1'

        save_customer_link(con,'testpay','cust-insights',3,'feature',A086)
        raw_feature=event('evt-feature-1','testpay','cust-insights','feature_active');assert ingest_signed_provider_event(con,raw_feature,expected_signature(raw_feature,secret),secret)['reconciliationStatus']=='reconciled'
        assert addon_status(con,3,A086)['source']=='provider_verified'
        raw_cancel=event('evt-feature-2','testpay','cust-insights','feature_cancelled');ingest_signed_provider_event(con,raw_cancel,expected_signature(raw_cancel,secret),secret);assert addon_status(con,3,A086)['active'] is False

        raw_unlinked=event('evt-unlinked','testpay','nobody','feature_active');u=ingest_signed_provider_event(con,raw_unlinked,expected_signature(raw_unlinked,secret),secret);assert u['reconciliationStatus']=='unlinked'
        summary=reconciliation_summary(con);assert summary['summary']['reconciled']==3 and summary['summary']['unlinked']==1 and 'Only signature-verified provider events' in summary['boundary']
        assert len(coupons_admin(con))==3
        print('EGM4000 billing controls passed: usage metering, retention, coupons, signed reconciliation')
        con.close()
    finally:
        try:os.unlink(path)
        except OSError:pass

if __name__=='__main__':main()
