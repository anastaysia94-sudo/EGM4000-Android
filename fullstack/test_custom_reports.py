#!/usr/bin/env python3
"""A087 custom report package persistence and safety contracts."""
from __future__ import annotations

import os
import sqlite3
import tempfile

from storage import Connection
from custom_reports import (
    admin_requests,
    create_request,
    migrate_custom_reports,
    my_requests,
    public_packages,
    save_package,
    update_request,
)


def expect_error(code, fn):
    try:
        fn()
    except ValueError as exc:
        assert str(exc) == code, (code, exc)
    else:
        raise AssertionError(f"expected {code}")


def main():
    fd,path=tempfile.mkstemp(prefix='egm4000-a087-',suffix='.db');os.close(fd)
    try:
        raw=sqlite3.connect(path);raw.row_factory=sqlite3.Row;con=Connection(raw,False)
        migrate_custom_reports(con)
        pkg=save_package(con,{
            'title':'Personal Evidence Deep Dive',
            'description':'Human-reviewed analysis of user-authorized recorded evidence.',
            'deliverables':['Rolling 30-day evidence review','Pattern and uncertainty notes','Actionable tracking checklist'],
            'price_label':'$49 external checkout',
            'turnaround_label':'2 business days',
            'status':'active',
        })
        catalog=public_packages(con)
        assert catalog['packages'][0]['id']==pkg['id']
        assert 'does not prove payment' in catalog['billingBoundary']
        req=create_request(con,42,{'package_id':pkg['id'],'request_note':'Focus on pacing and break consistency.'})
        assert req['status']=='requested' and req['paymentStatus']=='external_unverified'
        expect_error('active_report_request_exists',lambda:create_request(con,42,{'package_id':pkg['id']}))
        req=update_request(con,req['id'],{'status':'in_progress','payment_status':'external_unverified','owner_note':'Review started.'})
        assert req['status']=='in_progress'
        expect_error('delivery_content_required',lambda:update_request(con,req['id'],{'status':'delivered','payment_status':'external_unverified'}))
        expect_error('https_delivery_url_required',lambda:update_request(con,req['id'],{'status':'delivered','payment_status':'external_unverified','delivery_url':'http://example.com/report'}))
        expect_error('private_delivery_url_not_allowed',lambda:update_request(con,req['id'],{'status':'delivered','payment_status':'external_unverified','delivery_url':'https://127.0.0.1/report'}))
        delivered=update_request(con,req['id'],{'status':'delivered','payment_status':'external_unverified','delivery_note':'Your report is ready.','delivery_url':'https://example.com/report.pdf'})
        assert delivered['status']=='delivered' and delivered['deliveryUrl'].startswith('https://')
        mine=my_requests(con,42);assert mine['requests'][0]['status']=='delivered'
        owner=admin_requests(con);assert owner['summary']=={'total':1,'open':0,'delivered':1}
        print('EGM4000 A087 passed: package catalog, request intake, fulfillment, delivery validation, honest payment boundary')
        con.close()
    finally:
        try:os.unlink(path)
        except OSError:pass

if __name__=='__main__':main()
