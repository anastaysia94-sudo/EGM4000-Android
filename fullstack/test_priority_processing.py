#!/usr/bin/env python3
"""A077 priority-processing entitlement, queue-order, ownership, and safety contracts."""
from __future__ import annotations

import os
import sqlite3
import tempfile

from custom_reports import create_request, migrate_custom_reports, save_package, update_request
from priority_processing import (
    admin_priority_queue,
    apply_priority,
    grant_entitlement,
    migrate_priority_processing,
    my_priority_status,
    remove_priority,
    revoke_entitlement,
)
from storage import Connection


def expect_error(code, fn):
    try:
        fn()
    except ValueError as exc:
        assert str(exc) == code, (code, exc)
    else:
        raise AssertionError(f"expected {code}")


def main():
    fd, path = tempfile.mkstemp(prefix="egm4000-a077-", suffix=".db"); os.close(fd)
    try:
        raw = sqlite3.connect(path); raw.row_factory = sqlite3.Row; con = Connection(raw, False)
        con.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT,display_name TEXT,status TEXT)")
        con.execute("INSERT INTO users VALUES(1,'pilot1','Pilot One','active')")
        con.execute("INSERT INTO users VALUES(2,'pilot2','Pilot Two','active')")
        con.commit()
        migrate_custom_reports(con)
        migrate_priority_processing(con)

        package = save_package(con, {
            'title': 'Personal Evidence Deep Dive',
            'description': 'Historical evidence review.',
            'deliverables': ['Evidence summary'],
            'price_label': '$49 external checkout',
            'turnaround_label': 'Owner-estimated turnaround',
            'status': 'active',
        })
        r1 = create_request(con, 1, {'package_id': package['id'], 'request_note': 'Pilot one'})
        r2 = create_request(con, 2, {'package_id': package['id'], 'request_note': 'Pilot two'})

        initial = my_priority_status(con, 1)
        assert initial['entitlement']['active'] is False
        assert len(initial['requests']) == 1 and initial['requests'][0]['priority'] is False
        assert 'not proof of payment' in initial['paymentBoundary']
        assert 'does not guarantee a completion time' in initial['serviceBoundary']
        expect_error('priority_entitlement_required', lambda: apply_priority(con, 1, r1['id']))
        expect_error('unsupported_priority_entitlement_source', lambda: grant_entitlement(con, 1, 'provider_verified', 'must fail', 99))
        expect_error('priority_entitlement_user_not_found', lambda: grant_entitlement(con, 999, 'complimentary', '', 99))

        ent1 = grant_entitlement(con, 1, 'complimentary', 'QA access', 99)
        assert ent1['active'] is True and ent1['source'] == 'complimentary'
        p1 = apply_priority(con, 1, r1['id'])
        assert p1['active'] is True and p1['requestId'] == r1['id']
        expect_error('priority_report_request_not_found', lambda: apply_priority(con, 1, r2['id']))

        queue = admin_priority_queue(con)
        assert queue['queue'][0]['requestId'] == r1['id']
        assert queue['queue'][0]['priority'] is True and queue['queue'][0]['queuePosition'] == 1
        assert queue['queue'][1]['requestId'] == r2['id'] and queue['queue'][1]['priority'] is False
        assert 'provider_verified' not in queue['allowedSources']

        removed = remove_priority(con, 1, r1['id'])
        assert removed['active'] is False
        queue2 = admin_priority_queue(con)
        assert all(not row['priority'] for row in queue2['queue'])

        apply_priority(con, 1, r1['id'])
        revoked = revoke_entitlement(con, 1, 'QA revoke', 99)
        assert revoked['active'] is False
        status_after_revoke = my_priority_status(con, 1)
        assert status_after_revoke['requests'][0]['priority'] is False
        expect_error('priority_entitlement_required', lambda: apply_priority(con, 1, r1['id']))

        ent2 = grant_entitlement(con, 1, 'manual_external_unverified', 'external process deliberately unverified', 99)
        assert ent2['active'] is True and ent2['source'] == 'manual_external_unverified'
        update_request(con, r1['id'], {
            'status': 'delivered',
            'payment_status': 'external_unverified',
            'delivery_note': 'Delivered for queue-state test.',
        })
        expect_error('priority_requires_open_report_request', lambda: apply_priority(con, 1, r1['id']))

        print('EGM4000 A077 passed: real queue ordering, owned-request scope, grant/revoke controls, no fake payment or speed guarantee')
        con.close()
    finally:
        try: os.unlink(path)
        except OSError: pass


if __name__ == '__main__':
    main()
