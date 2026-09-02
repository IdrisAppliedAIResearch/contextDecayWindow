# HH-005 Pre-Registration - semantic plus DA aspect-v2

**Status:** `COMPLETE - NO_ASPECT_V2_IMPROVEMENT; 32k competitive but lower`
**Date:** September 1, 2026
**Predecessors:** HH-003 semantic+ASPECT-v1 and HH-004 DA-only ablation

## 1. Question

On the exact 842-item NF-004/HH overlap, does replacing HH-003's protected
ASPECT-v1 half with the frozen DA-098 derivative allocation improve live answer
quality while preserving the semantic half and additive recency path?

## 2. Arms

The only paid arm is `A_SEMANTIC_DA_ASPECT_V2`. Reuse the sealed HH-003
`A_EPISODIC_ASPECT` answers and judgements as the primary comparator. Do not
rerun any control.

For each item preserve HH-003 ASPECT-on's latest-32 recent episodes and its
initial semantic half exactly in source episode order. The initial semantic
count is `semantic_count - returned_semantic_count`; returned semantic slack is
not part of the protected half. Its rendered channel must remain at or below
16,000 characters.

Replace ASPECT-v1 with DA-098 allocation SHA
`f5327a9b5946f217910f2de5df222da66bda59d5f7b18267f8154763f98d44f9`.
Visit `arch32.selected_members` in frozen order. Exclude members already present
in recency or the protected semantic channel, then independently admit exact
decoded members under a separate 16,000-character derivative-channel budget,
skipping overflow and continuing. Preserve member order and identity. No
evidence, answer, category, rubric, prior model output, or outcome enters
allocation.

This is semantic + aspect-v2, not semantic + aspect-v1 + DA. ASPECT-v1 members
and returned semantic slack are absent from the treatment.

## 3. Population And Harness

Use the same 842 stable items and six-conversation counts registered in HH-004.
Use the unchanged HH-003/HH-004 answer and judge prompts,
`gpt-4o-mini-2024-07-18`, temperature 0, synchronous transport, eight workers,
answer pacing 6.6 RPM plus 170k TPM, and judge pacing 170k TPM. Pilot the first
eight `conv-26` items and reuse them in the full run.

## 4. Gates

Before paid calls: verify corpus, DA-098, HH-003 context/prediction/judgement
hashes; exact 842 joins; exact recency and semantic extraction; <=16k per
long-term channel; no duplicate dialogue members; DA-v2 non-inertness; DA-v2
allocation independent of ASPECT-v1 membership; byte-identical replay;
committed contexts and runner hashes; clean tracked tree.

Seal all 842 answers before full judging. Resume only absent stable keys. A
supervisor writes health every 30 seconds, detects 20-minute checkpoint stalls,
and performs at most five stable-key restarts. After 842 judgements, report
binary score, F1, exact match, category/conversation cells, tokens, latency,
failures, malformed labels, and a two-sided exact paired sign test against the
842-item ASPECT-v1 comparator.

## 5. Interpretation

No directional bar or automatic adoption is registered. LoCoMo and DA-098 are
spent, the comparator is cross-date, and this tests decoded source text rather
than compact pointer interpretation. It does not establish fresh transfer or
production concurrency.

## 6. Result

On 842 matched items, semantic+DA-v2 scored 649 (`.7708`) at 16k and 654
(`.7767`) at 32k, versus ASPECT-v1's 670 (`.7957`). Against ASPECT-v1, 16k
traded 26 gains/47 losses (net -21, p=`.0186`) and 32k traded 32/48 (net -16,
p=`.0929`). The 32k-versus-16k contrast was 27/22 (net +5, p=`.568`). Mean F1
was `.4435`/`.4469` versus `.4500`. No item failed or produced a malformed
judgement. The registered disposition is `NO_ASPECT_V2_IMPROVEMENT`.
