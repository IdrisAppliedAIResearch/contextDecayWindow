# LoCoMo Corpus Acquisition and Split Lock

**Document type:** Pre-exploration corpus lock, not a study registration
**Status:** `LOCKED BEFORE QA CONTENT OR OUTCOMES WERE OPENED`
**Authorized by:** User, August 13, 2026
**Source manifest:** `artifacts/source_manifest.json`
**Local dataset:** `C:\Users\muzaf\Downloads\locomo10.json`
**Date:** August 13, 2026

## 1. Purpose

This acquisition supplies the untouched external corpus authorized as Track B
in the NF-003 handoff. It does not register a mechanism, choose study bars, or
authorize a holdout run. Its only jobs are to bind the source bytes and reserve
independent conversations before exploratory outcomes can be computed.

LoCoMo is the first-choice corpus because this repository already names it as
unrun, its official question-answer records include dialogue IDs for evidence
when available, and its ten conversations preserve session and turn boundaries.
Those properties make episode-level delivery measurable without a model-based
evidence labeler.

## 2. Source lock

- Official repository: `https://github.com/snap-research/locomo`
- Repository commit: `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`
- Source path: `data/locomo10.json`
- Git blob SHA-1: `d95b872480b413d935821fdc3c84f8a8f5f29e73`
- Downloaded bytes: `2,805,274`
- Downloaded-file SHA-256: `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`
- License: Creative Commons Attribution-NonCommercial 4.0 International
- License source: `https://github.com/snap-research/locomo/blob/3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376/LICENSE.txt`

The dataset remains outside git, matching the LongMemEval convention. The
manifest, not a copy of the licensed corpus, is the repository artifact.

## 3. What was inspected before this lock

Only source metadata was opened: byte count, file hash, top-level sample count,
the ten `sample_id` values, and the first record's top-level key names. No
conversation text, QA question, answer, category, evidence list, per-split QA
count, retrieval output, or treatment/control comparison was opened.

## 4. Split rule

The split carries NF-002's pre-existing `40/60` development/holdout proportion
and program seed `5005`. The unit is a whole conversation, not a QA item, so
questions sharing dialogue history cannot leak across the boundary.

For each `sample_id`, compute:

```text
sha256("5005\0locomo-nf-successor-split-v1\0" + sample_id)
```

Sort ascending by that digest. The first four conversations are development;
the remaining six are holdout. The exact assignment is in the source manifest.

This lock does not claim that four conversations provide adequate development
power or that six provide adequate confirmatory power. Those are PF4 and PF9
questions for the successor registration. If the instrument cannot support
reachable bars at this split, the design stops; the holdout is not redrawn.

## 5. Access boundary

- Development: `conv-41`, `conv-47`, `conv-48`, `conv-42`
- Holdout: `conv-49`, `conv-30`, `conv-44`, `conv-26`, `conv-50`, `conv-43`

Development QA and dialogue content may be used for mandatory Preflight Part 1.
Holdout QA content and all holdout outcomes remain sealed until a successor
pre-registration with PF1-PF10 and both disposition tiers is committed.

No NF-003 Track A result may depend on LoCoMo. Track A remains a LongMemEval
characterization; Track B is a separate successor so a confirmatory claim does
not inherit NF-003's already-seen outcomes.
