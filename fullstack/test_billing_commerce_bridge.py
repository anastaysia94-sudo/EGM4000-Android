#!/usr/bin/env python3
"""A095 signed commerce reconciliation contracts for A082/A083."""
from __future__ import annotations
from datetime import datetime,timezone
import json,os,sqlite3,tempfile
from storage import Connection
from commercial_suite import migrate_commercial_suite
from billing_controls import expected_signature,migrate_billing_controls,reconciliation_summary
from marketplace_licensing import create_marketplace_order,get_marketplace_order,migrate_marketplace_licensing,save_listing,white_label_status
from billing_commerce_bridge import ingest_signed_commerce_event,save_commerce_customer_link


def event(event_id,customer,event_type):
    return json.dumps({'event_id':event_id,'provider':'testpay','customer_ref':customer,'event_type':event_type,'status':'active' if event_type.endswith(('paid','active')) else 'cancelled','occurred_at':datetime.now(timezone.utc).replace(microsecond=0).isoformat()},separators=(',',':')).encode()


def expect(code,fn,kind=ValueError):
    try:fn()
    except kind as exc:assert str(exc)==code,(code,exc)
    else:raise AssertionError(f'expected {code}')


def main():
    fd,path=tempfile.mkstemp(prefix='egm4000-commerce-recon-',suffix='.db');os.close(fd)
    try:
        raw=sqlite3.connect(path);raw.row_factory=sqlite3.Row;con=Connection(raw,False)
        con.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT,display_name TEXT,status TEXT NOT NULL DEFAULT 'active')")
        for uid,name in [(1,'Owner'),(2,'Coach'),(3,'Buyer')]:con.execute("INSERT INTO users VALUES(?,?,?,'active')",(uid,f'u{uid}',name))
        con.commit();migrate_commercial_suite(con);migrate_billing_controls(con);migrate_marketplace_licensing(con)
        listing=save_listing(con,2,{'title':'Evidence Review','price_cents':5000,'platform_fee_bps':1000,'status':'active'})
        order=create_marketplace_order(con,3,listing['id'],'Review my authorized evidence')
        assert order['paymentStatus']=='external_unverified'

        save_commerce_customer_link(con,'testpay','buyer-market',3,'marketplace_order',order['id'])
        expect('marketplace_billing_user_mismatch',lambda:save_commerce_customer_link(con,'testpay','wrong-buyer',2,'marketplace_order',order['id']))
        save_commerce_customer_link(con,'testpay','buyer-license',3,'white_label',str(3))
        expect('white_label_billing_user_mismatch',lambda:save_commerce_customer_link(con,'testpay','bad-license',3,'white_label','2'))

        secret='unit-test-commerce-signing-key'
        paid=event('evt-market-paid','buyer-market','marketplace_paid')
        expect('billing_signature_invalid',lambda:ingest_signed_commerce_event(con,paid,'sha256=wrong',secret),PermissionError)
        result=ingest_signed_commerce_event(con,paid,expected_signature(paid,secret),secret);assert result['reconciliationStatus']=='reconciled'
        assert get_marketplace_order(con,order['id'])['paymentStatus']=='provider_verified'
        assert get_marketplace_order(con,order['id'])['providerRef']=='evt-market-paid'
        duplicate=ingest_signed_commerce_event(con,paid,expected_signature(paid,secret),secret);assert duplicate['duplicate'] is True

        reversed_event=event('evt-market-reversed','buyer-market','marketplace_reversed')
        ingest_signed_commerce_event(con,reversed_event,expected_signature(reversed_event,secret),secret)
        assert get_marketplace_order(con,order['id'])['paymentStatus']=='external_unverified'
        assert get_marketplace_order(con,order['id'])['providerRef']=='evt-market-reversed'

        active=event('evt-wl-active','buyer-license','white_label_active')
        ingest_signed_commerce_event(con,active,expected_signature(active,secret),secret)
        wl=white_label_status(con,3);assert wl['license']['active'] is True and wl['license']['source']=='provider_verified' and wl['license']['sourceRef']=='evt-wl-active'
        cancelled=event('evt-wl-cancel','buyer-license','white_label_cancelled')
        ingest_signed_commerce_event(con,cancelled,expected_signature(cancelled,secret),secret)
        assert white_label_status(con,3)['license']['active'] is False

        unlinked=event('evt-commerce-unlinked','nobody','marketplace_paid')
        u=ingest_signed_commerce_event(con,unlinked,expected_signature(unlinked,secret),secret);assert u['reconciliationStatus']=='unlinked'
        summary=reconciliation_summary(con);assert summary['summary']['reconciled']==4 and summary['summary']['unlinked']==1
        assert all(e['verification_status']=='signature_verified' for e in summary['events'])
        print('EGM4000 signed commerce reconciliation passed: marketplace + white-label provider verification')
        con.close()
    finally:
        try:os.unlink(path)
        except OSError:pass

if __name__=='__main__':main()
