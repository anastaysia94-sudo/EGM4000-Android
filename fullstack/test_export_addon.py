#!/usr/bin/env python3
"""A076 entitlement, ownership, export-integrity, and payment-boundary contracts."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile

from export_addon import (
    admin_export_status,
    generate_artifact,
    get_artifact,
    grant_entitlement,
    migrate_export_addon,
    revoke_entitlement,
    user_export_status,
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
    fd, path = tempfile.mkstemp(prefix="egm4000-a076-", suffix=".db"); os.close(fd)
    try:
        raw = sqlite3.connect(path); raw.row_factory = sqlite3.Row; con = Connection(raw, False)
        con.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,username TEXT,display_name TEXT,status TEXT)")
        con.execute("CREATE TABLE gameplay_sessions(id INTEGER PRIMARY KEY,user_id INTEGER,platform TEXT,started_at TEXT,duration_min INTEGER,starting_bankroll REAL,spend REAL,payout REAL,shots INTEGER,hits INTEGER,notes TEXT,source TEXT)")
        con.execute("CREATE TABLE tips(id INTEGER PRIMARY KEY,user_id INTEGER,session_id INTEGER,created_at TEXT,title TEXT,body TEXT,evidence TEXT,confidence TEXT)")
        con.execute("INSERT INTO users VALUES(1,'pilot1','Pilot One','active')")
        con.execute("INSERT INTO users VALUES(2,'pilot2','Pilot Two','active')")
        con.execute("INSERT INTO gameplay_sessions VALUES(101,1,'Fire Kirin','2026-09-01T10:00:00+00:00',30,100,12.5,9.5,200,42,'owned session','authorized_capture')")
        con.execute("INSERT INTO gameplay_sessions VALUES(202,2,'Juwa','2026-09-01T11:00:00+00:00',20,50,6,4,100,10,'OTHER_USER_SENTINEL','authorized_capture')")
        con.execute("INSERT INTO tips VALUES(301,1,101,'2026-09-01T10:30:00+00:00','Compare repeated evidence','Historical-only coaching','200 shots / 42 hits','medium')")
        con.execute("INSERT INTO tips VALUES(302,2,202,'2026-09-01T11:30:00+00:00','OTHER_USER_TIP','Nope','Nope','low')")
        con.commit()
        migrate_export_addon(con)

        initial = user_export_status(con, 1)
        assert initial['entitlement']['active'] is False
        assert 'not proof of payment' in initial['paymentBoundary']
        expect_error('export_addon_entitlement_required', lambda: generate_artifact(con, 1, 'json'))
        expect_error('unsupported_entitlement_source', lambda: grant_entitlement(con, 1, 'provider_verified', 'fake provider claim', 99))
        expect_error('entitlement_user_not_found', lambda: grant_entitlement(con, 999, 'complimentary', '', 99))

        ent = grant_entitlement(con, 1, 'complimentary', 'QA access', 99)
        assert ent['active'] is True and ent['source'] == 'complimentary'

        artifact = generate_artifact(con, 1, 'json')
        assert artifact['rowCount'] == 2 and artifact['format'] == 'json'
        assert hashlib.sha256(artifact['content'].encode('utf-8')).hexdigest() == artifact['sha256']
        payload = json.loads(artifact['content'])
        assert payload['userId'] == 1 and payload['summary']['sessionCount'] == 1 and payload['summary']['tipCount'] == 1
        assert payload['summary']['historicalHitRate'] == 0.21
        assert 'does not predict random outcomes' in payload['historicalBoundary']
        assert 'OTHER_USER_SENTINEL' not in artifact['content'] and 'OTHER_USER_TIP' not in artifact['content']
        assert 'password' not in artifact['content'].lower() and 'token' not in artifact['content'].lower()

        csv_artifact = generate_artifact(con, 1, 'csv')
        assert csv_artifact['rowCount'] == 2 and 'gameplay_session' in csv_artifact['content'] and 'coaching_tip' in csv_artifact['content']
        assert 'OTHER_USER_SENTINEL' not in csv_artifact['content']
        assert len(user_export_status(con, 1)['artifacts']) == 2
        same = get_artifact(con, 1, artifact['id'])
        assert same['sha256'] == artifact['sha256'] and same['content'] == artifact['content']
        expect_error('export_artifact_not_found', lambda: get_artifact(con, 2, artifact['id']))

        owner = admin_export_status(con)
        assert owner['artifactCount'] == 2 and owner['entitlements'][0]['userId'] == 1
        assert 'provider_verified' not in owner['allowedSources']

        revoked = revoke_entitlement(con, 1, 'QA revoke', 99)
        assert revoked['active'] is False
        expect_error('export_addon_entitlement_required', lambda: generate_artifact(con, 1, 'json'))
        ent2 = grant_entitlement(con, 1, 'manual_external_unverified', 'external process, deliberately unverified', 99)
        assert ent2['active'] is True and ent2['source'] == 'manual_external_unverified'

        print('EGM4000 A076 passed: gated owned-data exports, persistent hashes, no cross-user leakage, no fake payment verification')
        con.close()
    finally:
        try: os.unlink(path)
        except OSError: pass


if __name__ == '__main__':
    main()
