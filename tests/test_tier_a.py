#!/usr/bin/env python3
"""Regression tests for tier_a_check.py. Run with: python3 tests/test_tier_a.py
No test framework dependency -- plain asserts, stdlib only, matching the
rest of this skill's zero-dependency design.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKILL_ROOT, "scripts"))

import tier_a_check  # noqa: E402

RULES = json.loads(open(os.path.join(SKILL_ROOT, "rules", "tx_il_rules.json")).read())
HAYMAKER = open(os.path.join(HERE, "fixtures", "haymaker_brief.txt")).read()


def by_id(results, rule_id):
    for r in results:
        if r["id"] == rule_id:
            return r
    raise AssertionError(f"rule {rule_id} not found in results")


def test_state_detection_is_tx_only():
    results = tier_a_check.run(HAYMAKER, RULES)
    info = by_id(results, "_state_detection")
    assert "TX" in info["reason"] and "IL" not in info["reason"], info["reason"]


def test_il_only_rule_does_not_fire_on_tx_brief():
    """Regression test for the real bug hit while scoping this: an IL-only
    entity check ran unconditionally and flagged a TX-only brief."""
    results = tier_a_check.run(HAYMAKER, RULES)
    il_entity = by_id(results, "il-entity-name")
    assert il_entity["status"] == "N/A", f"expected N/A, got {il_entity['status']}"


def test_tx_entity_checks_pass_on_haymaker():
    results = tier_a_check.run(HAYMAKER, RULES)
    assert by_id(results, "tx-rep-cert")["status"] == "PASS"
    assert by_id(results, "tx-entity-name")["status"] == "PASS"


def test_no_banned_flood_words_in_haymaker():
    results = tier_a_check.run(HAYMAKER, RULES)
    for rid in ["1.7-a", "1.7-b", "1.7-c", "1.7-d", "1.7-e", "1.7-f"]:
        assert by_id(results, rid)["status"] == "PASS", f"{rid} unexpectedly flagged"


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
