# AF-PRE-001 RESULTS — sample-120 scoring, disposition per Amendment 001

Run date 2026-09-20. Arms, bars, and gold fixed in `AMENDMENT_001_surface_and_gold.md` (commit `117d1083`) before any score. All numbers **characterization** (partition ruling); no confirmation claim is possible on LoCoMo.

## Top-1 anchor accuracy (gold = earliest-evidence turn)

| Arm | top-1 | Wilson 95% |
|---|---|---|
| LEX | 0/120 (0.00) | registered as expected: natural questions carry no quoted spans |
| BM25 | 29/120 (0.242) | [0.174, 0.326] |
| QWEN-BI (deployed bi-encoder) | 5/120 (0.042) | [0.018, 0.094] |
| CE (MiniLM, zero-training) | 25/120 (0.208) | [0.145, 0.290] |

Paired contrasts (McNemar exact, two-sided):
- CE vs LEX: net +25, p < 1e-6
- CE vs QWEN-BI: net +20, p = 8.8e-5
- **CE vs BM25: net −4 (CE-only 6, BM25-only 10), p = 0.454**

## Disposition: **NO_SIGNAL**

`WORKS` requires CE net ≥ +10 vs *every* baseline with p < .05 — it loses to BM25. `SIGNAL` requires every pairwise direction non-negative — CE vs BM25 is −4. Per Amendment 001 the reading stands: **zero-training discriminative anchor localization is not demonstrated over the lexical floor**, and over the deployed bi-encoder only at the cost of losing to BM25. Per §9.2 this is an instrument statement, not a verdict on the anchor idea.

## Failure mechanisms (diagnosed, not post-hoc decorated)

- **BM25 wins with the answer-in-evidence effect:** LoCoMo evidence turns tend to lexically mirror their questions (gold BM25-rank often 1). The lexical floor is inflated by dataset annotation style, exactly the confound §3 registered.
- **QWEN-BI's collapse is question-echo:** its top-1 is systematically the partner's echoed question ("What was your favorite game…?" outranks the answer turn). Verified by rank inspection: gold cosines 0.37–0.65 are not far off, but echoes score higher. Same failure class as CE fixture F2.
- **CE ≈ BM25 overall but they disagree productively** (16 discordant pairs): CE trades BM25's keyword hits for the ms-marco answer-seeking bias, which wins on some items (F4/F5-style direct answers) and loses on duplex/meta pairs (F1–F3-style). The fixture gate predicted this profile before the run — that is the instrument working.
- **Ceiling reality check:** top-1 exact-anchor accuracy is a brutal metric — even the best arm finds the single gold turn ~1 in 4. Anchor *set* inclusion (product semantics: anchor + all before) would rank much higher; exact top-1 overstates the gap between arms.

## DEVIATION — E-fidelity line expectation was wrong

Amendment 001 pre-stated "LEX and BM25 take 17/17" on the E-anchor gap. Observed: all four arms 0/17. Investigation (`_inspect_tmp.py` runs, artifacts in `e_fidelity_note.json`): under **top-1** semantics BM25 ranks the meeting anchor at rank 108/140, because the query asks for a *delivery location* and the record lines ("The team reviewed delivery records for X…") lexically dominate the meeting line ("The meeting X review took place…"), which contains no answer tokens. The expectation was an authoring error (inclusion semantics mistaken for top-1). Recorded as deviation; not evidence of a scoring bug — the 17 anchors are exactly where the anchor *event* exists but is not an *answer*, which independently supports the program's standing claim that availability ≠ answerability.

## Artifacts
- `part1_artifacts/sample120_results.json` — per-item hits, contrasts, E line.
- `part1_artifacts/sample120_audit_items.json` — the 34 earliest≠latest items with all four arm predictions, for the user audit. Audit cannot flip the disposition (CE vs BM25 already negative; per Amendment it only *protects* against spurious SIGNAL).
- `part1_artifacts/fixture_gate_both.json`, `fixture_gate_lex_bm25.json` — pre-run instrument evidence.

## What this closes and opens
- Closes AF-PRE-001 as an honest NO_SIGNAL: zero-shot MiniLM reranking is not a drop-in anchor identifier — it is at lexical parity and shares the bi-encoder's echo confusion. No native-reader pilot is triggered (the WORKS binding never fired).
- Opens the sharper question the data now poses: BM25's 29 hits ride answer-in-evidence lexical overlap; the anchors the product actually needs are E-style *event* turns (meeting/announcement lines) where lexical and embedding top-1 both demonstrably fail (E line: 0/17 for every arm). A successor should define anchor targets as event-boundary turns with explicit question→event semantics, not answer-bearing evidence turns.
