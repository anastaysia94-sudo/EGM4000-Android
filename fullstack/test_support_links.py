#!/usr/bin/env python3
"""A092 optional support-link safety and measurement contracts."""
from __future__ import annotations

import os
import sqlite3
import tempfile

from storage import Connection
from support_links import admin_support_links,archive_support_link,migrate_support_links,public_support_links,resolve_support_click,save_support_link


def expect_error(code,fn):
    try:fn()
    except ValueError as exc:assert str(exc)==code,(code,exc)
    else:raise AssertionError(f'expected {code}')


def main():
    fd,path=tempfile.mkstemp(prefix='egm4000-a092-',suffix='.db');os.close(fd)
    try:
        raw=sqlite3.connect(path);raw.row_factory=sqlite3.Row;con=Connection(raw,False)
        migrate_support_links(con)
        link=save_support_link(con,{'title':'Support EGM4000','body':'Help fund evidence-first educational tools.','destination_url':'https://example.com/support','active':True})
        assert link['active'] is True and link['clicks']==0
        public=public_support_links(con);assert public['optional'] is True and len(public['links'])==1
        assert 'destinationUrl' not in public['links'][0]
        assert 'does not prove a donation' in public['boundary']
        resolved=resolve_support_click(con,link['id']);assert resolved['destinationUrl']=='https://example.com/support'
        owner=admin_support_links(con);assert owner['links'][0]['clicks']==1
        assert 'does not infer or claim donation amounts' in owner['measurementBoundary']
        expect_error('https_destination_required',lambda:save_support_link(con,{'title':'Bad','destination_url':'http://example.com/support','active':True}))
        expect_error('private_destination_not_allowed',lambda:save_support_link(con,{'title':'Bad','destination_url':'https://127.0.0.1/support','active':True}))
        expect_error('unsafe_guarantee_claim',lambda:save_support_link(con,{'title':'Guaranteed profit support','destination_url':'https://example.com/no','active':True}))
        archived=archive_support_link(con,link['id']);assert archived['active'] is False
        assert resolve_support_click(con,link['id']) is None
        print('EGM4000 A092 passed: optional support, safe HTTPS, aggregate clicks, no payment inference')
        con.close()
    finally:
        try:os.unlink(path)
        except OSError:pass

if __name__=='__main__':main()
