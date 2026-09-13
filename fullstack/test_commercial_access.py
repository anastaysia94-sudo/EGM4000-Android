#!/usr/bin/env python3
"""C008 commercial-access contracts: A080 live path and A084 engine readiness."""
from __future__ import annotations

import os
import sqlite3
import tempfile

from storage import Connection
from commercial_access import (
    admin_affiliates,
    admin_api_clients,
    api_evidence_summary,
    api_platform_summary,
    archive_affiliate,
    authorize_api_client,
    migrate_commercial_access,
    record_affiliate_signup,
    record_api_usage,
    resolve_affiliate_click,
    rotate_api_client_key,
    save_affiliate,
    save_api_client,
)


def expect_error(code, fn):
    try:
        fn()
    except ValueError as exc:
        assert str(exc) == code, (code, exc)
    else:
        raise AssertionError(f"expected {code}")


def main():
    fd, path = tempfile.mkstemp(prefix="egm4000-commercial-", suffix=".db")
    os.close(fd)
    try:
        raw = sqlite3.connect(path)
        raw.row_factory = sqlite3.Row
        con = Connection(raw, False)
        migrate_commercial_access(con)
        con.execute("CREATE TABLE gameplay_sessions(id INTEGER PRIMARY KEY,platform TEXT)")
        con.execute("CREATE TABLE live_sessions(id INTEGER PRIMARY KEY,platform TEXT)")
        con.execute("CREATE TABLE normalized_events(id INTEGER PRIMARY KEY,evidence_type TEXT,platform TEXT)")
        con.execute("INSERT INTO gameplay_sessions(id,platform) VALUES(1,'Fire Kirin'),(2,'Fire Kirin'),(3,'Juwa')")
        con.execute("INSERT INTO live_sessions(id,platform) VALUES(1,'Fire Kirin')")
        con.execute("INSERT INTO normalized_events(id,evidence_type,platform) VALUES(1,'observed_evidence','Fire Kirin'),(2,'observed_evidence','Fire Kirin'),(3,'estimate','Juwa')")
        con.commit()

        partner = save_affiliate(con, {"label": "Evidence Creator", "code": "CREATOR-7", "landing_path": "/", "active": True})
        assert partner["code"] == "CREATOR-7" and partner["clicks"] == 0
        assert resolve_affiliate_click(con, "creator-7")["code"] == "CREATOR-7"
        assert record_affiliate_signup(con, "CREATOR-7", 42) is True
        assert record_affiliate_signup(con, "CREATOR-7", 42) is False
        owner = admin_affiliates(con)
        assert owner["partners"][0]["clicks"] == 1
        assert owner["partners"][0]["signups"] == 1
        assert owner["partners"][0]["conversionRate"] == 1.0
        assert "raw IP" in owner["privacy"]
        expect_error("reserved_landing_path", lambda: save_affiliate(con, {"label": "Bad", "code": "BAD-REF", "landing_path": "/api/private"}))
        archived = archive_affiliate(con, partner["id"])
        assert archived["active"] is False and resolve_affiliate_click(con, "CREATOR-7") is None

        client = save_api_client(con, {"name": "Research client", "plan": "developer", "scopes": ["summary", "evidence"], "daily_quota": 2, "active": True})
        key = client.pop("apiKey")
        assert key.startswith("egm_api_")
        stored = con.execute("SELECT key_hash,key_prefix FROM api_access_clients WHERE id=?", (client["id"],)).fetchone()
        assert key not in stored["key_hash"] and stored["key_prefix"] == key[:16]
        row, used, quota = authorize_api_client(con, key, "summary")
        assert used == 0 and quota == 2
        assert api_platform_summary(con)["historicalSessions"][0]["platform"] == "Fire Kirin"
        record_api_usage(con, row, "summary", "/api/developer/platform-summary")
        row, used, quota = authorize_api_client(con, key, "evidence")
        assert used == 1
        assert api_evidence_summary(con)["evidence"][0]["event_count"] == 2
        record_api_usage(con, row, "evidence", "/api/developer/evidence-summary")
        expect_error("api_daily_quota_exceeded", lambda: authorize_api_client(con, key, "summary"))
        rotated = rotate_api_client_key(con, client["id"])
        new_key = rotated.pop("apiKey")
        expect_error("invalid_api_key", lambda: authorize_api_client(con, key, "summary"))
        expect_error("api_daily_quota_exceeded", lambda: authorize_api_client(con, new_key, "summary"))
        listing = admin_api_clients(con)
        assert listing["clients"][0]["usedToday"] == 2
        assert "SHA-256" in listing["security"]
        print("EGM4000 C008 commercial access passed: A080 attribution + A084 engine contracts")
        con.close()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


if __name__ == "__main__":
    main()
