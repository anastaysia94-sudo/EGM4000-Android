from collections import Counter

from admin_registry import ADMIN_CAPABILITIES, BY_ID, EVIDENCE, IMPLEMENTED, PROVIDER_CONFIG


def main():
    assert len(ADMIN_CAPABILITIES) == 100
    assert len(BY_ID) == 100
    assert IMPLEMENTED == set(range(1, 101))
    assert PROVIDER_CONFIG == set()

    expected_ids = [f"A{i:03d}" for i in range(1, 101)]
    assert [item["id"] for item in ADMIN_CAPABILITIES] == expected_ids

    counts = Counter(item["implementation_status"] for item in ADMIN_CAPABILITIES)
    assert counts == {"implemented": 100}

    assert set(EVIDENCE) == set(range(1, 101))
    for item in ADMIN_CAPABILITIES:
        assert item["title"].strip()
        assert item["category"].strip()
        assert item["evidence"].strip()
        assert "not yet implemented" not in item["evidence"].lower()
        assert "missing" not in item["evidence"].lower()

    print("C007 Admin 100 registry verified: 100 implemented / 0 modelled / 0 provider-config-required")


if __name__ == "__main__":
    main()
