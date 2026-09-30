#!/usr/bin/env python3
"""Tier A: deterministic, zero-LLM checks against a brief's raw text.
No model call anywhere in this file -- pure string/regex matching against
rules compiled from the TX/IL checklist docs. Same input -> same output, always.

Every rule is gated by detected state before it runs (see detect_states).
A rule with no "state" key applies regardless of state.
"""
import json
import re
import sys


def detect_states(text_lower):
    states = set()
    if any(k in text_lower for k in ["puct", "oncor", "centerpoint", "tdu", "base texas rep", "texas"]):
        states.add("TX")
    if any(k in text_lower for k in ["comed", "illinois", "base retail"]):
        states.add("IL")
    return states


def _state_applies(rule, detected_states):
    rule_state = rule.get("state")
    if not rule_state:
        return True
    return rule_state in detected_states


def run(brief_text, rules):
    text_lower = brief_text.lower()
    detected_states = detect_states(text_lower)
    results = [{
        "id": "_state_detection", "section": "n/a", "status": "INFO",
        "reason": f"Detected state(s): {sorted(detected_states) or ['NONE']}",
        "note": "Keyword-based; only gates which state-specific rules below run. Not a substitute for Tier C confirming applicability.",
    }]

    for rule in rules["banned_phrases"]:
        if not _state_applies(rule, detected_states):
            results.append({"id": rule["id"], "section": rule["section"], "status": "N/A",
                             "reason": f"Rule scoped to {rule.get('state')}; brief not detected as that state.",
                             "note": rule["note"]})
            continue
        pat = rule["pattern"].lower()
        if pat in text_lower:
            idx = text_lower.index(pat)
            snippet = brief_text[max(0, idx - 40): idx + len(pat) + 40].replace("\n", " ")
            results.append({"id": rule["id"], "section": rule["section"], "status": "FLAG",
                             "reason": f"Banned phrase '{rule['pattern']}' found.",
                             "note": rule["note"], "evidence": f"...{snippet}..."})
        else:
            results.append({"id": rule["id"], "section": rule["section"], "status": "PASS",
                             "reason": f"Banned phrase '{rule['pattern']}' not found.", "note": rule["note"]})

    for rule in rules["flag_for_manual_review_phrases"]:
        if not _state_applies(rule, detected_states):
            results.append({"id": rule["id"], "section": rule["section"], "status": "N/A",
                             "reason": f"Rule scoped to {rule.get('state')}; brief not detected as that state.",
                             "note": rule["note"]})
            continue
        pat = rule["pattern"].lower()
        if pat in text_lower:
            idx = text_lower.index(pat)
            snippet = brief_text[max(0, idx - 40): idx + len(pat) + 40].replace("\n", " ")
            results.append({"id": rule["id"], "section": rule["section"], "status": "NEEDS_JUDGMENT",
                             "reason": f"Phrase '{rule['pattern']}' found -- requires human/Tier C judgment, not auto-passable.",
                             "note": rule["note"], "evidence": f"...{snippet}..."})
        else:
            results.append({"id": rule["id"], "section": rule["section"], "status": "N/A",
                             "reason": f"Trigger phrase '{rule['pattern']}' not present.", "note": rule["note"]})

    for rule in rules["conditional_required_blocks"]:
        if not _state_applies(rule, detected_states):
            results.append({"id": rule["id"], "section": rule["section"], "status": "N/A",
                             "reason": f"Rule scoped to {rule.get('state')}; brief not detected as that state.",
                             "note": rule["note"]})
            continue
        triggered = any(t.lower() in text_lower for t in rule["trigger_any"])
        if not triggered:
            results.append({"id": rule["id"], "section": rule["section"], "status": "N/A",
                             "reason": "No trigger keyword present.", "note": rule["note"]})
            continue
        missing = [r for r in rule["require_all"] if r.lower() not in text_lower]
        if missing:
            results.append({"id": rule["id"], "section": rule["section"], "status": "FLAG",
                             "reason": f"Trigger present but required block missing: {missing}",
                             "note": rule["note"]})
        else:
            results.append({"id": rule["id"], "section": rule["section"], "status": "PASS",
                             "reason": "Trigger present and required block found.", "note": rule["note"]})

    for rule in rules["entity_presence_checks"]:
        if not _state_applies(rule, detected_states):
            results.append({"id": rule["id"], "section": rule["section"], "status": "N/A",
                             "reason": f"Brief not detected as targeting {rule.get('state')}; rule doesn't apply.",
                             "note": rule["note"]})
            continue
        if rule.get("regex"):
            found = re.search(rule["pattern"], text_lower) is not None
        else:
            found = rule["pattern"] in text_lower
        results.append({"id": rule["id"], "section": rule["section"], "status": "PASS" if found else "FLAG",
                         "reason": f"Pattern '{rule['pattern']}' {'found' if found else 'NOT found'} in text.",
                         "note": rule["note"]})

    return results


if __name__ == "__main__":
    brief_text = open(sys.argv[1]).read()
    rules = json.loads(open(sys.argv[2]).read())
    print(json.dumps(run(brief_text, rules), indent=2))
