#!/usr/bin/env python3
"""Scans a brief's raw text and returns typed claims for Tier A/B to check.
Stdlib only. No model call. Extraction only -- produces no verdicts.
"""
import re
import json
import sys


def find_numeric_comparisons(text):
    pattern = re.compile(
        r'(\d{1,3})%\s*(less|cheaper|below)\s*(?:than|the)?\s*(?:a |the )?([a-zA-Z ]{3,30})',
        re.I,
    )
    return [
        {
            "type": "numeric_comparison",
            "value": int(m.group(1)),
            "comparator": m.group(2),
            "against": m.group(3).strip(),
            "snippet": m.group(0),
        }
        for m in pattern.finditer(text)
    ]


def find_testimonial_mentions(text):
    trigger_words = [
        "testimonial", "quote", "review", "rating", "member said",
        "endorsement", "influencer", "ambassador", "investor",
    ]
    hits = []
    for w in trigger_words:
        for m in re.finditer(re.escape(w), text, re.I):
            window = text[max(0, m.start() - 80): m.start() + 80]
            names = re.findall(r'\b[A-Z][a-z]+(?: [A-Z][a-z]+)?\b', window)
            hits.append({
                "type": "testimonial",
                "trigger": w,
                "candidate_names": names,
                "snippet": window.strip(),
            })
    return hits


def find_promo_mentions(text):
    triggers = ["promo", "promotion", "bill credit", "gift card", "referral"]
    return [{"type": "promo", "trigger": t} for t in triggers if t.lower() in text.lower()]


def detect_states(text):
    text_lower = text.lower()
    states = set()
    if any(k in text_lower for k in ["puct", "oncor", "centerpoint", "tdu", "base texas rep", "texas"]):
        states.add("TX")
    if any(k in text_lower for k in ["comed", "illinois", "base retail"]):
        states.add("IL")
    return sorted(states)


if __name__ == "__main__":
    text = open(sys.argv[1]).read()
    result = {
        "detected_states": detect_states(text),
        "claims": (
            find_numeric_comparisons(text)
            + find_testimonial_mentions(text)
            + find_promo_mentions(text)
        ),
    }
    print(json.dumps(result, indent=2))
