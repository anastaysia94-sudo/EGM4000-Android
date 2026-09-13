#!/usr/bin/env python3
"""C008 provider-independent asset contract tests."""
from __future__ import annotations

import os
import sqlite3
import tempfile

from storage import Connection
from monetization_assets import (
    KIND_CAPABILITY,
    admin_assets,
    archive_asset,
    migrate_monetization_assets,
    public_catalog,
    resolve_click,
    save_asset,
    validate_destination,
)


def expect_error(code, fn):
    try:
        fn()
    except ValueError as exc:
        assert str(exc) == code, (code, exc)
    else:
        raise AssertionError(f"expected {code}")


def main():
    fd, path = tempfile.mkstemp(prefix="egm4000-c008-assets-", suffix=".db")
    os.close(fd)
    try:
        raw = sqlite3.connect(path)
        raw.row_factory = sqlite3.Row
        con = Connection(raw, False)
        migrate_monetization_assets(con)

        expect_error("https_destination_required", lambda: validate_destination("http://example.com/offer"))
        expect_error("private_destination_not_allowed", lambda: validate_destination("https://127.0.0.1/private"))

        created = []
        examples = {
            "partner_referral": "Partner learning resource",
            "sponsored_education": "Sponsored evidence course",
            "hardware_referral": "Capture hardware guide",
            "course_upsell": "Advanced evidence literacy course",
            "promo_bundle": "Evidence review bundle",
        }
        for kind, title in examples.items():
            asset = save_asset(
                con,
                1,
                {
                    "kind": kind,
                    "title": title,
                    "body": "Optional educational resource. Results remain uncertain and evidence-based.",
                    "price_label": "$19" if kind == "promo_bundle" else "Optional",
                    "destination_url": f"https://example.com/{kind}",
                    "active": True,
                },
            )
            assert asset["capabilityId"] == KIND_CAPABILITY[kind]
            assert asset["active"] is True
            created.append(asset)

        sponsor = next(x for x in created if x["kind"] == "sponsored_education")
        assert sponsor["disclosure"] == "Sponsored educational placement."

        expect_error(
            "unsafe_guarantee_claim",
            lambda: save_asset(
                con,
                1,
                {
                    "kind": "promo_bundle",
                    "title": "Guaranteed profit bundle",
                    "destination_url": "https://example.com/nope",
                    "active": True,
                },
            ),
        )

        public = public_catalog(con)
        assert public["schema"] == "egm.monetization-catalog.v1"
        assert len(public["assets"]) == 5
        assert all("destinationUrl" not in x for x in public["assets"])
        assert any(x["sponsored"] is True for x in public["assets"])

        first = created[0]
        resolved = resolve_click(con, first["slug"])
        assert resolved and resolved["destinationUrl"].startswith("https://")
        owner = admin_assets(con)
        row = next(x for x in owner["assets"] if x["id"] == first["id"])
        assert row["clicks"] == 1
        assert "raw IP" in owner["privacy"]

        archive_asset(con, first["id"], 1)
        assert resolve_click(con, first["slug"]) is None
        assert len(public_catalog(con)["assets"]) == 4
        print("EGM4000 C008 provider-independent assets passed: 5 kinds, safe URLs/claims, redirects, aggregate clicks, archive")
        con.close()
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


if __name__ == "__main__":
    main()
