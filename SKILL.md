---
name: creative-brief-compliance-qa
description: Runs Base Power's TX/IL marketing compliance checklist against a creative brief -- a tiered check (deterministic pattern matching, live cross-reference against external sources, then LLM judgment only where nothing else can resolve it) that reports every finding with why it matters. Advisory only, never blocks. Use when asked to "check this brief for compliance," "run compliance QA on this brief," "is this brief compliant," "run the checklist on this brief," or when reviewing a Creative > Briefs page before it goes to LRP.
---

# Creative brief compliance QA

Checks one Base Power creative brief against Carter Copeland's TX/IL Copy Compliance Checklist. Three tiers, in order of how much you should trust them:

- **Tier A** (`scripts/tier_a_check.py`) -- pure regex/string matching, zero model calls, deterministic. Handles banned phrases, required verbatim disclaimer blocks, entity-name presence.
- **Tier B** (`scripts/tier_b_site_check.py` for live-site checks; Drive-folder checks are agent-run, see step 5) -- live cross-reference against external sources that can drift out of sync with the brief. Deterministic execution, but only as reliable as its assumption about where evidence lives.
- **Tier C** -- your own judgment, for what's left: misleading-impression calls, which disclosure actually applies, entity blur. Always a draft for LRP, never a verdict.

**This is advisory only.** Never tell anyone the brief is blocked or can't proceed. Report findings; LRP/Growth-lead sign-off remains mandatory regardless of what this check finds.

## Steps

**1. Get the brief text locally.** Fetch the brief page (via the Notion connector). Write its raw text content to a scratch file -- nothing below this point works on Notion content directly, it all needs a local file.

**2. Run detection.**
```
python3 scripts/detect_claims.py <brief.txt>
```
Returns detected state(s) and a list of typed claims (numeric comparisons, testimonial mentions, promo mentions). This doesn't judge anything -- it just tags what's present, for the next two tiers to use.

**3. Run Tier A.**
```
python3 scripts/tier_a_check.py <brief.txt> rules/tx_il_rules.json
```
Before trusting this file's rule list, re-fetch both checklist docs live (Drive doc IDs are in `rules/tx_il_rules.json`'s `source` block) and compare their "Date changed" line against `date_changed_seen` in that file. If they differ, say so in the report -- the rules file may be behind the actual checklist.

**4. Run the live-site part of Tier B.**
```
python3 scripts/tier_b_site_check.py <brief.txt> rules/tier_b_sources.json
```
This only covers claims with a registered source in `tier_b_sources.json` (currently: the generator-cost-comparison claim against basepowercompany.com). If it reports `NEEDS_REVIEW` because the site's regex found nothing, don't assume compliant -- the site copy likely changed and the entry needs updating.

**5. Run the Drive-folder part of Tier B yourself -- this cannot be a script.** A subprocess can't use the authenticated Drive MCP connection, so you do this directly:
- For any testimonial/consent claim detected in step 2, search the consent folder (`1CJhsbUxhuweZtzYsVnD7AkzJud9T5lId`) for the person's name.
- For any claim needing substantiation, search the substantiation folder (`1Xswy76XUpCTaTTCtD9PdrCs7GQSzXnS-`).
- **Before reporting "not found" as a finding**, check `rules/tier_b_sources.json`'s `known_alternate_locations` for that claim type. Investor/business/paid-partner relationships (e.g. JJ Watt) get filed under supplier contracts, not the marketing consent repository -- a miss there is not evidence of a missing consent form. If the brief itself links directly to evidence, verify that link instead of searching; a direct link beats discovery-by-search every time one is available.

**6. Do the Tier C read.** Re-fetch both checklist docs live (don't rely on memory or on the rules file's summarized version). Read the brief in full, including any self-written "Flags"/self-review section. For every checklist item Tier A/B didn't already resolve, and for every item where Tier A/B's result seems inconsistent with your own read of the brief, produce a verdict: PASS / FLAG / N/A / NEEDS-LRP, with the specific evidence you're basing it on. If your read disagrees with a Tier A/B result, say so explicitly as a discrepancy for LRP to look at -- don't silently override a deterministic result, and don't silently defer to it either.

**7. Report.** One item per checklist rule that applied, most severe first: rule -> what's in the brief -> why it matters -> what would confirm/resolve it. Close with what this check could not verify (any visual/logo check, anything needing a link the brief didn't provide). Post as a comment on the brief's Notion page.

## Known limitations (read before trusting a clean run)

- No visual/logo checks -- entirely text-based, in this version.
- The `flag_for_manual_review_phrases` and `conditional_required_blocks` trigger keywords in `tx_il_rules.json` are a crude first pass -- a paraphrase of a banned claim or a comparison phrased without the exact trigger word slips through Tier A undetected. Widening this list is ongoing work, not a solved problem.
- `ad-disclosure` in the rules file is explicitly low-recall -- don't treat its PASS as proof a disclosure exists.
- Tier B's Drive checks are only as good as the org's actual filing conventions. The JJ Watt case is the concrete example: a technically-correct search still produced a wrong real-world conclusion.

## Reproducibility

This skill's rule files (`rules/tx_il_rules.json`, `rules/tier_b_sources.json`) are the single source of truth for what Tier A/B check. If you find a gap or a bug (like the state-gating bug this design already hit once), fix it here and add a regression test to `tests/test_tier_a.py` against the golden fixture in `tests/fixtures/` -- don't fix it only in your own head for this one run. For this to actually be reproducible for other team members, this skill needs to be published through the org's shared skill sync rather than left as a local-only copy -- confirm that's been done before relying on someone else getting the same behavior you get.
