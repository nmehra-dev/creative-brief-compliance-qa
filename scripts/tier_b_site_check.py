#!/usr/bin/env python3
"""Tier B, the pure-HTTP part only: fetch a live external source with curl
and diff a claim in the brief against it. No model call.

This file deliberately does NOT attempt the Drive-folder checks -- those need
the authenticated MCP connection, which a subprocess script cannot use. See
SKILL.md step 5: the agent runs those directly and applies
rules/tier_b_sources.json's known_alternate_locations before treating a
"not found" result as a real finding.
"""
import json
import re
import subprocess
import sys


def curl_raw_html(url):
    result = subprocess.run(
        ["curl", "-s", "-A", "Mozilla/5.0", url],
        capture_output=True, text=True, timeout=20,
    )
    return result.stdout


def check_numeric_comparisons(brief_text, sources):
    findings = []
    for source in sources:
        pattern = re.compile(source["extract_regex"], re.I)
        brief_matches = pattern.findall(brief_text)
        if not brief_matches:
            continue
        html = curl_raw_html(source["url"])
        site_matches = pattern.findall(html)
        brief_val = brief_matches[0] if isinstance(brief_matches[0], str) else brief_matches[0][0]
        if not site_matches:
            findings.append({
                "claim": source["claim_pattern"], "status": "NEEDS_REVIEW",
                "reason": f"Brief claims a value ({brief_val}) but the live page pattern found nothing -- "
                          f"either the site copy changed or the regex is stale. Update rules/tier_b_sources.json, don't assume compliant.",
                "url": source["url"],
            })
            continue
        site_val = site_matches[0] if isinstance(site_matches[0], str) else site_matches[0][0]
        if str(brief_val) != str(site_val):
            findings.append({
                "claim": source["claim_pattern"], "status": "FLAG",
                "reason": f"Brief says {brief_val}, live site currently says {site_val}.",
                "url": source["url"],
            })
        else:
            findings.append({
                "claim": source["claim_pattern"], "status": "PASS",
                "reason": f"Brief and live site both say {brief_val}.",
                "url": source["url"],
            })
    return findings


if __name__ == "__main__":
    brief_text = open(sys.argv[1]).read()
    sources = json.loads(open(sys.argv[2]).read())["numeric_comparison_sources"]
    print(json.dumps(check_numeric_comparisons(brief_text, sources), indent=2))
