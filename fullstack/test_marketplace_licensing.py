#!/usr/bin/env python3
"""Contracts for A082 creator/coach marketplace fee and A083 white-label licensing."""
from __future__ import annotations
import os,sqlite3,tempfile
from storage import Connection
from marketplace_licensing import *


def expect(code,fn,kind=ValueError):
    try:fn()
    except kind as exc:assert str(exc)==code,(code,exc)
    else:raise AssertionError(f'expected {code}')


def main():
    fd,path=tempfile.mkstemp(prefix='egm4000-market-',suffix='.db');os.close(fd)
    try:
        raw=sqlite3.connect(path);raw.row_factory=sqlite3.Row;con=Connection(raw,False)
        con.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT,display_name TEXT,status TEXT NOT NULL DEFAULT 'active')")
        for uid,name in [(1,'Owner'),(2,'Coach Two'),(3,'Buyer Three'),(4,'Buyer Four')]:con.execute("INSERT INTO users VALUES(?,?,?,'active')",(uid,f'u{uid}',name))
        con.commit();migrate_marketplace_licensing(con)

        listing=save_listing(con,2,{'title':'Evidence Review Session','description':'Review authorized recorded evidence and tracking quality.','service_label':'Written evidence review','price_cents':10000,'platform_fee_bps':1500,'status':'active'})
        assert listing['coachUserId']==2 and listing['priceCents']==10000 and listing['platformFeePercent']==15.0
        cat=marketplace_catalog(con);assert len(cat['listings'])==1 and 'does not prove payment' in cat['feeBoundary'] and 'must not promise winnings' in cat['safetyBoundary']
        expect('cannot_order_own_listing',lambda:create_marketplace_order(con,2,listing['id']))

        order=create_marketplace_order(con,3,listing['id'],'Focus on pacing and evidence completeness.')
        assert order['paymentStatus']=='external_unverified' and order['grossCents']==10000 and order['platformFeeCents']==1500 and order['creatorNetCents']==8500
        expect('active_marketplace_order_exists',lambda:create_marketplace_order(con,3,listing['id']))
        assert get_marketplace_order(con,order['id'],buyer_user_id=4) is None
        expect('marketplace_order_not_found',lambda:update_marketplace_order(con,4,order['id'],'accepted'))
        accepted=update_marketplace_order(con,2,order['id'],'accepted');assert accepted['status']=='accepted' and accepted['paymentStatus']=='external_unverified'
        expect('marketplace_delivery_note_required',lambda:update_marketplace_order(con,2,order['id'],'delivered'))
        delivered=update_marketplace_order(con,2,order['id'],'delivered','Delivered evidence-quality review; no outcome prediction included.');assert delivered['status']=='delivered'
        m=my_marketplace(con,2);assert len(m['sales'])==1 and len(m['listings'])==1 and 'signed A095' in m['boundary']
        admin=marketplace_admin(con);assert admin['summary']['providerVerified']==0 and admin['summary']['verifiedPlatformFeeCents']==0
        assert 'never treated as collected revenue' in admin['boundary']
        verified=provider_verify_marketplace_order(con,order['id'],'evt-market-verified');assert verified['paymentStatus']=='provider_verified' and verified['providerRef']=='evt-market-verified'
        admin=marketplace_admin(con);assert admin['summary']['providerVerified']==1 and admin['summary']['verifiedPlatformFeeCents']==1500
        provider_cancel_marketplace_payment(con,order['id'],'evt-market-reversed');assert get_marketplace_order(con,order['id'])['paymentStatus']=='external_unverified'

        st=white_label_status(con,3);assert st['license']['active'] is False
        expect('white_label_license_required',lambda:save_white_label_profile(con,3,{'brand_name':'Buyer Brand'}),PermissionError)
        expect('unsupported_manual_license_source',lambda:grant_white_label(con,3,'provider_verified'))
        licensed=grant_white_label(con,3,'external_unverified','External agreement awaiting provider reconciliation');assert licensed['license']['active'] and licensed['license']['source']=='external_unverified'
        prof=save_white_label_profile(con,3,{'brand_name':'Evidence Harbor','support_label':'Evidence Support','logo_url':'https://example.com/logo.png','accent_label':'aqua','footer_text':'Licensed evidence workspace'})
        assert prof['profile']['brand_name']=='Evidence Harbor' and prof['profile']['logo_url']=='https://example.com/logo.png'
        preview=white_label_preview(con,3);assert preview['brandName']=='Evidence Harbor' and preview['poweredBy']=='EGM4000 / SmartPickShop Holdings' and 'does not alter evidence provenance' in preview['boundary']
        expect('https_url_required',lambda:save_white_label_profile(con,3,{'brand_name':'Bad','logo_url':'http://example.com/logo.png'}))
        expect('private_url_not_allowed',lambda:save_white_label_profile(con,3,{'brand_name':'Bad','logo_url':'https://127.0.0.1/logo.png'}))
        provider=provider_verify_white_label(con,3,'evt-license-verified');assert provider['license']['source']=='provider_verified' and provider['license']['sourceRef']=='evt-license-verified'
        owner=white_label_admin(con);assert len(owner['licenses'])==1 and 'signed A095 reconciliation' in owner['boundary']
        revoke_white_label(con,3,'Agreement ended');assert white_label_status(con,3)['license']['active'] is False
        expect('white_label_license_required',lambda:white_label_preview(con,3),PermissionError)

        print('EGM4000 marketplace/licensing passed: fee ledger, ownership, delivery, licensed branding and safe provider boundary')
        con.close()
    finally:
        try:os.unlink(path)
        except OSError:pass

if __name__=='__main__':main()
