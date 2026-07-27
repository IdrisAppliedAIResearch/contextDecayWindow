# Breadth Regression Audit

## Scope and integrity

This diagnostic was read-only with respect to preserved study artifacts. No file
under `experiments/study_010/` was enumerated, read, written, or hashed. No
llama.cpp endpoint was contacted and no inference or embedding call was made.
Writes were confined to `experiments/analysis/`.

## 1. Premise verification

**The three formal gates pass, but the substantive premise does not.** The
committed Study 002 Condition C score artifact records 13.0/13.0:

| question | score | recorded rationale |
|---|---:|---|
| Q1 | 1 | Both correct: 847 meters, S460ML. Numbered list format applied. |
| Q2 | 1 | Both correct: Dr. Anara Bekova, 92.4 metric tons per axle. |
| Q3 | 1 | Both rules stated precisely: numbered list for specs, risk classification for engineering recommendations. |
| Q4 | 1 | All four correct: The Annunciation of Forlì, Melozzo da Forlì, Cardinal Giuliano della Rovere, 1483. |
| Q5 | 1 | Both correct: lead white ground, ultramarine glaze. |
| Q6 | 1 | Clean Renaissance retrieval. Correctly identifies della Rovere as patron and Papal Legate, explains significance as future Pope Julius II. No monetary policy or marine biology contamination. |
| Q7 | 1 | All four correct: Vampyroteuthis infernalis, Dr. Kenji Watanabe, 600–900 meters, marine snow particle aggregation. |
| Q8 | 1 | Organ: photophores correct. Locations include arm tips, mantle, post-ocular, fin tips. "Mantle" is a valid approximation of "mantle margin." Both organ type and location correct. |
| Q9 | 1 | Q6 response is clean Renaissance content with no cross-topic contamination. |
| Q10 | 1 | Q7 correctly attributes Vampyroteuthis research to Dr. Kenji Watanabe. No conflation with other researchers. |
| Q11 | 1 | Comprehensive response with structured retrieval across all four topics. Key entities and values present with correct attribution. |
| Q12 | 1 | Both rules stated correctly in Turn 114 response. |
| Q13 | 1 | Numbered list rule consistently applied in all visible turns (112, 113, 114, 115, 116, 117, 118, 119, 120). Risk classification rule N/A — no engineering recommendations in probe turns. |

Q11 is explicitly **1.0**. Its recorded rationale is: “Comprehensive response with structured retrieval across all four topics. Key entities and values present with correct attribution.”

The exact turn-120 user message is 227
UTF-8 bytes with SHA-256
`078ea5363a93ebb88810b079b20c626dbb04c72e4c2b876deb824e69be03e110` in Study
002, 003, 004, and the Study 005 script used by 005-009. It is byte-identical.

The historical `experiments/study_002/rubric_filled.md` blob is likewise
byte-identical at the accepted-run commits for 002, 003, 004, 005, 006, 007, and
009: 7,052 bytes, SHA-256
`4e88385d4cabbff0183782dbfe2682d3c0d9a57f18116ae48a0404ad3a5d6126`.
The working-tree byte count differs because Git checked it out with CRLF line
endings; historical identity is established from immutable LF-normalized blobs.

### Study 002 C Q11 answer

> <think>
> The user wants a comprehensive summary of all specific numerical values, named entities, and technical specifications established across four distinct topics in the conversation history:
> 1.  Bridge engineering
> 2.  Renaissance art
> 3.  Monetary policy
> 4.  Marine biology
> 
> I need to review the retrieved conversation history to extract these details.
> 
> **Topic 1: Bridge Engineering (Halcyon Crossing)**
> *   **Project Name:** Halcyon Crossing
> *   **Lead Engineer:** Dr. Anara Bekova
> *   **Main Span:** 847 meters
> *   **Steel Specification:** Grade S460ML
> *   **Load Rating:** 92.4 metric tons per axle
> *   **Bridge Type:** Long-span cable-stayed bridge
> *   **Deck Options Analyzed:** Orthotropic steel deck, Concrete deck, Composite deck
> *   **Failure Modes:** Fatigue, Buckling, Torsional Flutter/Aeroelastic Instability, Scour, Concrete Creep/Shrinkage, Seismic Response, Corrosion/Degradation
> *   **Analysis Methodology:** Dynamic load analysis (Modeling assumptions, Modal analysis, Load definition, Dynamic analysis methods, Load combinations, Verification)
> *   **Cable Inspection:** Acoustic Emission Monitoring, Magnetic Flux Leakage, Visual/Drone Inspection, Vibration Monitoring
> *   **Seismic Performance Objectives:** Immediate Occupancy (IO), Life Safety (LS), Collapse Prevention (CP)
> *   **Seismic Levels:** Design Earthquake (DE), Maximum Considered Earthquake (MCE)
> 
> **Topic 2: Renaissance Art**
> *   **Time Period:** 1470s and 1480s
> *   **Format:** Tondo (circular format)
> *   **Influences:** Ancient sculpture, architectural fragments
> *   **Motifs:** Garlands, putti, classical drapery, mythological figures
> *   **Compositional Strategies:** Architectural frames (loggia, temple fronts), figure grouping based on sculptural reliefs, triangular/pyramidal compositions, *Di sotto in sù* (perspective from below)
> *   **Theoretical Framework:** Neoplatonism, *disegno*
> *   **Painters Mentioned (implied/contextual):** Botticelli, Ghirlandaio, Mantegna
> 
> **Topic 3: Monetary Policy**
> *   *Note: The retrieved history does not contain a specific turn about monetary policy. It jumps from Renaissance art (Turn 52) to a rule check (Turn 114) to Marine Biology (Turn 119). Wait, let me check the history again.*
> *   *History Check:*
>     *   Turn 1-10: Bridge Engineering.
>     *   Turn 51-52: Renaissance Art.
>     *   Turn 114: Rule check.
>     *   Turn 119: Marine Biology.
> *   *Observation:* The user's prompt mentions "monetary policy" as one of the four topics. However, the provided retrieval history does not include any turns about monetary policy.
> *   *Action:* I must rely *only* on the provided retrieved conversation history. If the history doesn't show monetary policy, I cannot invent it. However, the user *asserts* we discussed it.
> *   *Correction:* Looking closely at the prompt "RETRIEVED CONVERSATION HISTORY", it might be truncated or selective. The user says "across all four topics in our entire conversation today". If the history provided doesn't have it, I should state what is in the history.
> *   *Wait, looking at Turn 52:* "Explain the full development of the tondo format..."
> *   *Looking at Turn 114:* "What are the two formatting rules..."
> *   *Looking at Turn 119:* "What specific bioluminescent organs..."
> *   *Missing:* Monetary Policy.
> *   *Hypothesis:* The user might be testing my ability to recall *only* what is in the context or asking a trick question. Or perhaps I missed it? No, scanning the turns: 1, 2, 3, 4, 5, 6, 7, 8, 9, 18, 51, 52, 114, 119. None are monetary policy.
> *   *Strategy:* I will list the details for the topics present in the history (Bridge Engineering, Renaissance Art, Marine Biology). I will note that the provided history does not contain a discussion on monetary policy, or I will simply omit it if I must strictly follow the "based on retrieved history" implicit instruction. However, the user asks "List... we established... in our entire conversation

Critical-fact marking:

- [x] civil: Halcyon Crossing
- [x] civil: 847
- [x] civil: Dr. Anara Bekova
- [x] civil: S460ML
- [x] civil: 92.4
- [ ] art: The Annunciation of Forli
- [ ] art: Melozzo da Forli
- [ ] art: Cardinal Giuliano della Rovere
- [ ] art: 1483
- [ ] monetary: Taylor Rule
- [ ] monetary: Federal Reserve
- [ ] monetary: Dr. Priya Mehta
- [ ] monetary: 2.3%
- [ ] marine: Vampyroteuthis infernalis
- [ ] marine: Dr. Kenji Watanabe
- [ ] marine: 600
- [ ] marine: marine snow

**Forensic contradiction:** the preserved answer ends exactly where reproduced
above, mid-sentence inside an unclosed `<think>` block. It has no final answer and
contains only 5 of the 17 locked facts. The recorded Q11=1.0
rationale is therefore inconsistent with the preserved answer. The nominal
cross-study “regression” is a scoring/provenance anomaly, not evidence that a
correct Study 002 breadth answer was later lost.

### Q11 scores since Study 002

| arm | Q11 | source artifact |
|---|---:|---|
| 003 accepted | 0.0 | `experiments/study_003/runs/run_001/condition_c/rubric/scores.md` |
| 004 treatment | 0.0 | `experiments/study_004/runs/study_004_full_002/condition_c/rubric/scores.md` |
| 004 control | 0.0 | `experiments/study_004/controls/v3_same_settings/v3_control_002/iterative/rubric/scores.md` |
| 005 treatment | 0.0 | `experiments/study_005/runs/study_005_full_001/condition_c/rubric/scores.md` |
| 005 control | 0.0 | `experiments/study_005/controls/promotion_seeded/promotion_seeded_001/condition_c/rubric/scores.md` |
| 006 treatment | 0.0 | `experiments/study_006/evaluation/rubric_scores.json` |
| 006 control | 0.0 | `experiments/study_006/evaluation/rubric_scores.json` |
| 007 treatment | 0.0 | `experiments/study_007/evaluation/rubric_scores.json` |
| 007 control | 0.0 | `experiments/study_007/evaluation/rubric_scores.json` |
| 009 L | 0.0 | `experiments/study_009/evaluation/rubric_scores.json` |
| 009 S | 0.0 | `experiments/study_009/evaluation/rubric_scores.json` |

No later listed arm scored above 0.0 on Q11.

## 2. Study 002 C turn-120 context

The complete byte-for-byte prompt is in `study_002_turn_120_prompt.txt`
(source SHA-256 `402d0765f150d2c5010f0e33df7b1f2595e1b2bed526c4a4dff7232be43f97e9`). Study 002's
constructed prompts and database are present on disk but git-ignored; provenance
comes from the preserved run directory and is hash-audited here.

| source turn | provenance | K similarity | decay | serialized chars | domain |
|---:|:---:|---:|---:|---:|---|
| 1 | K | 0.5524049401283264 | 0.9995865991403594 | 823 | civil |
| 2 | K | 0.5388032793998718 | 0.9995865989182291 | 233 | civil |
| 3 | N | n/a | 0.9995865988904628 | 4547 | civil |
| 4 | N | n/a | 0.9995865988904628 | 4346 | civil |
| 5 | N | n/a | 0.9995865988626965 | 4290 | civil |
| 6 | N | n/a | 0.9995865988349302 | 4831 | civil |
| 7 | N | n/a | 0.9995865988349302 | 4673 | civil |
| 8 | N | n/a | 0.9995865988071639 | 4642 | civil |
| 9 | N | n/a | 0.9995865988071639 | 4423 | civil |
| 18 | K | 0.5195809602737427 | 0.9391627477803703 | 4800 | civil |
| 51 | K | 0.6156581044197083 | 0.9601467655037772 | 4432 | art |
| 52 | N | n/a | n/a | 152 | art |
| 114 | K | 0.5257587432861328 | 0.997272076231262 | 709 | other |
| 119 | N | n/a | 1.0 | 2072 | marine |

| domain | episodes | serialized chars |
|---|---:|---:|
| civil | 10 | 37608 |
| art | 2 | 4584 |
| monetary | 0 | 0 |
| marine | 1 | 2072 |
| other | 1 | 709 |

K=5 threshold-clearing hits:

| source turn | domain | similarity |
|---:|---|---:|
| 1 | civil | 0.5524049401283264 |
| 2 | civil | 0.5388032793998718 |
| 18 | civil | 0.5195809602737427 |
| 51 | art | 0.6156581044197083 |
| 114 | other | 0.5257587432861328 |

**No. The prompt contains civil, art, and marine material, but no monetary
episode.** It contains
6 of the 17 locked fact strings:
Halcyon Crossing, 847, Dr. Anara Bekova, S460ML, 92.4, Vampyroteuthis infernalis.

## 3. Why K collapsed

### Preserved evidence

The logs preserve only K hits at or above 0.50, not the full candidate
distribution. At turns 116/119/120, Study 002 has
[5, 0, 5] hits and Study
009 S has [1, 0, 0].

### Cannot be reconstructed without inference

The requested full similarity distributions, min/max/mean/median, near-miss
counts, length-similarity correlations, raw query vectors, and cross-run query
vector cosine are **not recoverable from preserved artifacts**. Both databases
store episode embeddings; neither stores query embeddings. The retrieval logs
store only threshold-clearing similarities. Turn-120's stored episode embedding
is not a substitute: both accepted runners embed
`User: <message>\nAssistant: <response>` when storing an episode, whereas K
queries embed the user message alone.

Regenerating the missing vector would require an embedding inference and exact
historical embedding runtime. This audit intentionally made none. The most
supported mechanism is trajectory-induced episode-text thinning and changed
episode embeddings: identical query text and unchanged K parameters operated on
different stored assistant responses. Confirmation requires preserved query
vectors/full scores or an explicitly authorized deterministic embedding replay;
refutation would be identical candidate embeddings with divergent scores.

## 4. Cross-arm breadth at turn 120

| arm | total chars | records | civil chars | art chars | monetary chars | marine chars | facts | Q11 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Study 002 C | 45369 | 14 | 37608 | 4584 | 0 | 2072 | 6 | 1.0 |
| Study 003 accepted | 20551 | 11 | 18672 | 0 | 0 | 923 | 7 | 0.0 |
| Study 007 treatment | 60619 | 17 | 41034 | 4901 | 6265 | 7225 | 10 | 0.0 |
| Study 009 S | 21072 | 10 | 17824 | 0 | 0 | 2119 | 6 | 0.0 |
| Study 009 L | 60619 | 17 | 41034 | 4901 | 6265 | 7225 | 10 | 0.0 |

The full machine-readable table is `breadth_turn_comparison.csv`.

Study 002 did **not** have four-domain breadth. Ranked by evidential support:

1. **Scoring-artifact inconsistency: decisive.** The preserved answer is
   truncated reasoning with 5/17 facts, yet it received 1.0.
2. **Episode richness and total delivered volume: supported descriptively but
   ruled out as sufficient.** Study 002 is much larger, yet still lacks monetary
   context and does not produce a complete answer.
3. **K-hit composition: supported at the thresholded level but not breadth.**
   Study 002 had five K hits, all from civil, art, or rule turns; none was
   monetary or marine.
4. **Per-domain balance: ruled out.** Study 002 has zero monetary characters.
5. **Prompt structure: plausible but untested.** Flat history gives each episode
   a simple turn header; tagged prompts add tier/provenance boundaries. No causal
   inference is possible without a controlled run.
6. **Absence of an LTM block: ruled out as a sufficient explanation.** Study 002
   succeeded without LTM, while Study 009 L had a large LTM block and still
   failed Q11; moreover, the preserved Study 002 answer did not actually succeed.

## 5. Episode-text thinning

| run | mean assistant chars | median | response budget | model/quantization | sampling |
|---|---:|---:|---|---|---|
| Study 002 C | 3986.2 | 4300.0 | not preserved in a launch manifest | not preserved in a launch manifest | not preserved in a launch manifest |
| Study 003 accepted | 2703.7 | 2778.0 | not preserved in a launch manifest | not preserved in a launch manifest | not preserved in a launch manifest |
| Study 005 treatment | 3497.0 | 3562.0 | not preserved in a launch manifest | not preserved in a launch manifest | not preserved in a launch manifest |
| Study 006 treatment | 3458.4 | 3561.5 | not recorded at top level | Qwen3.6-27B-UD-Q6_K_XL.gguf | seed=5005; temperature=1.0; top_k=20; top_p=0.949999988079071; min_p=0.0; repeat_penalty=1.0 |
| Study 007 treatment | 3682.0 | 3782.0 | not recorded at top level | Qwen3.6-27B-UD-Q6_K_XL.gguf | seed=5005; temperature=1.0; top_k=20; top_p=0.949999988079071; min_p=0.0; repeat_penalty=1.0 |
| Study 009 S | 2971.2 | 2966.0 | 2048 | Qwen3.6-27B-UD-Q6_K_XL.gguf | seed=5005; temperature=1.0; top_k=20; top_p=0.949999988079071; min_p=0.0; repeat_penalty=1.0 |
| Study 009 L | 3682.0 | 3782.0 | not recorded at top level | Qwen3.6-27B-UD-Q6_K_XL.gguf | seed=5005; temperature=1.0; top_k=20; top_p=0.949999988079071; min_p=0.0; repeat_penalty=1.0 |

The complete per-turn curves are in `response_length_trend.csv`. Missing
launch-manifest settings are reported as missing, not inferred from later runs.
Study 009 L is the accepted Study 007 artifact reused by Study 009, so those two
rows are intentionally identical.

From Study 002 C to Study 009 S, the delivered-record count ratio is
0.714, the mean stored-assistant-length ratio is
0.745, and their simple multiplicative prediction is
0.532 versus an observed retrieved-character ratio of
0.443. This decomposition is descriptive: shorter responses explain
most of the drop, with fewer records contributing the remainder; markup and
which turns were selected prevent exact multiplicative equality.

Using raw `len(user)+len(assistant)` on corresponding source turns gives a more
direct sequential decomposition: Study 002 selection with Study 002 text costs
48,616 chars; replacing only those turns with Study 009 text costs
30,563; then switching to Study 009's selected turns costs 18,569.
Thus shorter stored text accounts for 18,053 chars
(60.1%) of the drop and selection count/composition for
11,994 (39.9%). This allocation is
order-dependent and descriptive, not causal.

## 6. Prompt structure hypothesis

| Study 002 C flat history | Study 009 S tagged structure |
|---|---|
| system prompt | system prompt |
| `--- RETRIEVED CONVERSATION HISTORY ---` | `<pinned_rules>` |
| repeated `[Turn N]`, `User:`, `Assistant:` | `<recent_context>` with `<episode turn=... topic=...>` |
| `--- END HISTORY ---` | optional `<retrieved_stm>` with similarity attribute |
| current `User:` / `Assistant:` | `<current_turn>` |

Study 002 labels every item only by chronological turn and renders a single flat
history. Study 009 separates pinned rules, recency, and semantic retrieval;
episodes carry topic/tier metadata and XML delimiters. Both order episodes
chronologically within their rendered blocks, but the tagged form fragments the
history into architectural tiers. That could affect cross-domain enumeration,
but it is a hypothesis only; no inference was run to test it.

## 7. Rarity-signal feasibility

The IDF corpus contains exactly 120 Study 007 conversation turns, each treated as
one document. IDF is `ln((N+1)/(df+1))+1`; a fixed stop-word list defines content
words. The three variants are mean content-word IDF, maximum content-word IDF,
and sum IDF divided by the span's logged word count.

| plant | variant | score | rarity rank | minimum C | current density rank |
|---|---|---:|---:|---|---:|
| art_pigment | rarity_mean | 3.124831 | 412 | 412 | 316 |
| art_pigment | rarity_max | 4.186353 | 410 | 410 | 316 |
| art_pigment | rarity_sum_per_word | 2.120421 | 338 | 338 | 316 |
| art_patron_role | rarity_mean | 3.499571 | 295 | 295 | 240 |
| art_patron_role | rarity_max | 5.102643 | 328 | 328 | 240 |
| art_patron_role | rarity_sum_per_word | 1.899767 | 404 | 404 | 240 |
| monetary_taylor | rarity_mean | 3.262306 | 282 | 282 | 91 |
| monetary_taylor | rarity_max | 5.102643 | 9 | 9 | 91 |
| monetary_taylor | rarity_sum_per_word | 1.826892 | 389 | 389 | 91 |
| monetary_fed | rarity_mean | 3.131812 | 342 | 342 | 208 |
| monetary_fed | rarity_max | 5.102643 | 24 | 24 | 208 |
| monetary_fed | rarity_sum_per_word | 2.087874 | 334 | 334 | 208 |
| marine_photophores | rarity_mean | 3.310391 | unranked | unreachable: fails retained eligibility | unranked |
| marine_photophores | rarity_max | 4.186353 | unranked | unreachable: fails retained eligibility | unranked |
| marine_photophores | rarity_sum_per_word | 2.336746 | unranked | unreachable: fails retained eligibility | unranked |
| marine_feeding | rarity_mean | 3.140902 | 167 | 167 | 89 |
| marine_feeding | rarity_max | 4.409496 | 167 | 167 | 89 |
| marine_feeding | rarity_sum_per_word | 2.542635 | 77 | 77 | 89 |

`rarity_signal_feasibility.csv` also includes the top 10 non-rubric-critical
spans per topic for every variant, exposing the precision cost. Eligibility is
retained, so `marine_photophores` remains unreachable despite rarity because its
source span has no recognized entity or numeric token.

Separation guarantee: the IDF builder and rarity ranker read only the 120-turn
conversation and `span_inventory`. They do not read `q_facts_key.md`, any rubric,
or the plant list. The existing plant CSV is opened only after every span has
been scored and ranked; rubric-critical patterns are applied afterward solely to
label false positives.

## Hash verification

Zero drift across 6,673 pre/post-hashed files.

- study_002: 769 files; manifest SHA-256 `574c72710ac21d9e1f3d576aa2a370af3aee6bc9fb21208d1fd7dc66d659b109`.
- study_003: 1,270 files; manifest SHA-256 `86c2aea9e16ff4dc23c9825443479ac22305e72b395f6aa01d84adfeef745d5c`.
- study_004: 1,391 files; manifest SHA-256 `10b626b8058546ef0f9c2458d29bef163d9fc7e422c73a1225a16d95ec794e5e`.
- study_005: 1,254 files; manifest SHA-256 `e3af943ca29e0e71c065ce8936704cbd7d7d7d9e93d74dc6baed1b4f84ca985a`.
- study_006: 835 files; manifest SHA-256 `a8ca49628931ae995af77fc7835302fe8235896709952cce531133df3e1107f4`.
- study_007: 751 files; manifest SHA-256 `2870985a7c51518bb9c3c773172fac5ef92c1fb574ea7bb265156bf675ccdf85`.
- study_008: 16 files; manifest SHA-256 `553da1120be13bac95a44911d4d67e18a851f4c3a80c06e5e03ee9ab5c0d35cd`.
- study_009: 386 files; manifest SHA-256 `c6b09459117de5641a4487b044f3fc8303b4f6992382d67c39d9e8cdf08965eb`.

No path under `experiments/study_010/` participated in either inventory.
