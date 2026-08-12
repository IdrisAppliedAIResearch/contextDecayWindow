# SR-001 - Extractive Span Representation

**Type:** Pre-registered offline component study with conditional 35-turn ablation
**Date:** August 11, 2026
**Branch:** `study/sr-001-extractive-span-representation`
**Status:** PRE-REGISTERED - IMPLEMENTATION AND OUTCOME ACCESS PROHIBITED UNTIL AUTHORIZATION
**Predecessors:** BA-001 benchmark causal audit; TA-001 temporal-adjacency bridge
**Outcome ceiling:** `CHARACTERIZED`; no production adoption or full live run

## 1. Question and scope

BA-001 found a promising but confounded association: its historical span-dense
method produced 10 query gains, zero losses, and enumeration recall of 0.6250
versus 0.0625 for whole-episode dense retrieval. That comparison did not hold
retrieval identity fixed: M2 ranked 111 episodes while M5 ranked 3,268 spans.
TA-001 then showed that adding temporal neighbors recovered art but displaced
useful semantic seeds and caused six targeted regressions.

SR-001 adds exactly one component: **packable extractive sentence spans**. It
asks:

> With the complete source-episode ranking, scores, eligible population,
> query, and 32,000-character budget held identical, does changing only the
> packable representation from whole episodes to faithful sentence spans
> improve broad evidence delivery without any targeted or domain regression?

The component is motivated by extractive gist and detail separation in P8 of
`HYPOTHETICAL_001_MECHANICAL_BIOLOGICAL_MEMORY_MODEL.md`. It does not implement
consolidation: spans are created at read time, retain exact provenance, and do
not alter storage, accessibility, ranking, or future retrieval.

## 2. Immutable inputs

Every input is verified by raw-byte count and SHA-256 before execution. A
mismatch stops the study.

| Input | Bytes | SHA-256 |
|---|---:|---|
| Biological-memory reference | 17,505 | `DBC6A1C4134DF37877D6F5A77ACDF61DB4CE8361A1F7B2A2810B6182A6D6F926` |
| BA-001 report | 6,861 | `EFAA03B10A90DA68C7F284BB092A80D1EDBBB724A84D871CB89A5E4A4A18D14C` |
| BA-001 results | 41,619 | `1C0D6FB6EF01E991FD7F14EBBA2900D0770325C564B64648B9D716A84E1630F1` |
| Tier 2 retrieval rows | 23,523,340 | `97CE339F0CE50B3AF77C76F4707266C537349A20E8067361E45D65FD23FD9273` |
| Tier 2 evaluation rows | 674,786 | `4DD8AECC17B8F21D7F5DBCD2EE40249532662205D5A262F7180452D2587E8E50` |
| Q11 full-rank inventory | 10,642 | `8D6F9EEE6EBE232608981AAC0C0D4816EAEC4710AE551DB028AE0B323253AC03` |
| 121-turn episode database | 1,978,368 | `5DA47EA3FC2C8E3DCC50FA380FF65202D82557905D9976117E9E5D82E55C1C41` |
| Sealed 24-query manifest | 4,231 | `AE950FDA20DCE9F519F31EE2670A815A5599648CAB618D42309DB7E3F23D36F4` |
| Read-only query-vector cache | 249,856 | `D9741EDB0545D8CFE050663340599A31813D6025C38F0467E0EC7671573A1E6A` |
| Measurement-only answer key | 9,832 | `2D43A31D3C04F4AD690FF2910ABDE71F508A3F6CE776545A9F2B16F90FAE5320` |
| Locked sentence segmenter | 13,468 | `141C7EBDA6AF73DD7B69B00150DE200C03F65105F2E76AFD55FD9F767A8A5BDA` |
| Bakeoff packer and renderer | 4,075 | `737FFA0B182682A24F433259B4790308A374DFC8E9998402F2FCAFC1E1F9AADC` |
| Bakeoff corpus adapter | 8,031 | `3F87655AA794CEA8254F24A9C5BDA79B816852E5345A4BFC6F666CA6FED445F5` |

Q11 uses source turns 1-119. Each holdout query uses source turns 1-111. A
source episode is compared only by canonical SHA-256 of turn number, user text,
and assistant text. A span is compared by source content hash, role, start,
end, and exact UTF-8 text hash. Generated database IDs are provenance only.

The answer key is measurement-only. Component and Part 1 code may verify its
file hash but may not parse, import, or inspect it.

## 3. Fixed parameters and arms

These parameters are authoritative and are not swept:

```text
BUDGET_CHARS = 32000
Q11_ELIGIBLE_TURNS = 1..119
HOLDOUT_ELIGIBLE_TURNS = 1..111
SOURCE_RANK = descending frozen dense cosine, then source content SHA-256
SPAN_SEGMENTER = src.memory.span_segmenter.segment_episode
SPAN_FILTER = non-empty sentence spans only; no salience or eligibility filter
SPAN_ORDER_WITHIN_SOURCE = user before assistant, then ascending start/end offset
SOURCE_ORDER = frozen source-episode rank; spans never cross source-rank order
PACK_POLICY = exact serialized incremental cost, skip overflow, continue
```

### 3.1 C0 - whole-episode control

Rank every eligible source episode once by the frozen dense score. Convert each
ranked episode to the existing whole-episode candidate and apply the locked
bakeoff renderer and skip-overflow packer at 32,000 characters. C0 must
reproduce every committed M2 source-rank identity sequence, selected identity
sequence, payload digest, and delivered-character count for all 24 holdout
queries. Q11 must reproduce the committed fixed-query rank inventory and
whole-episode packed baseline.

### 3.2 T1 - source-rank-preserving spans

Use the exact C0 source ranking and score sequence. For each source episode in
rank order, call the locked Study 006 sentence segmenter and emit every
non-empty span in the fixed within-source order. Each span inherits its source
episode's dense score and rank; no span vector or query-span similarity exists.
Apply the same renderer semantics and skip-overflow policy at 32,000 characters,
charging each serialized span exactly.

T1 may read source rank, source score, turn, role, offsets, and source text. It
may not read domains, fact IDs, required terms, answer keys, rubrics, historical
gain/loss rows, span vectors, temporal neighbors, or measurement outcomes.

The complete ordered source-episode identity sequence must be byte-identical
between C0 and T1. Selected source identities may differ only because one arm
packs whole episodes and the other packs independently chargeable spans.

## 4. Part 1 - label-blind characterization

Part 1 runs C0 and T1 on Q11 and all 24 sealed holdout queries without opening
the answer key or counting facts. It records per query and arm:

- full ordered source identity and score sequences;
- source-rank equality across arms;
- span counts by role and source rank, span length distribution, and exact
  offset round trips;
- packed unit identities, packed source identities, omitted units, delivered
  characters, exact payload bytes, and payload SHA-256;
- sources delivered wholly, partially, or not at all in T1;
- boundary, empty-span, duplicate-text, oversized-unit, repeated-prefix, and
  budget-saturation behavior;
- zero generation calls, zero embedding calls, source hashes, command,
  environment, elapsed time, RSS, and output manifest.

Part 1 is repeated in a fresh process. Deterministic outputs excluding process
metadata must have one canonical digest.

The falsifiable behavioral identity is:

> T1 preserves C0's complete source rank exactly, replaces each episode only
> with faithful non-empty sentence spans in source-rank order, and changes no
> score or state; only independent span charging can alter delivery.

Part 1 passes only if all 25 source-rank sequences match across arms, every
span round-trips exactly to its source role and offsets, every payload is at
most 32,000 characters, all 24 C0 holdout payloads reproduce committed M2,
Q11 C0 reproduces its frozen baseline, two processes agree, and forbidden
label sentinels stop loudly. Otherwise disposition is
`REPRESENTATION_MECHANICS_INVALID` and the study stops before labels.

## 5. Final design lock and Preflight

After Part 1 is committed, a standalone final-design file binds its commit,
deterministic digest, unchanged Section 3 policy, C0 reproduction identities,
and eligibility. It contains no facts, domains, recall, gains, losses, or art
outcomes. It is committed before measurement code runs.

Part 1 is Preflight Part 1. After the final lock, PF1-PF10 execute in order:

| Check | Required executed evidence |
|---|---|
| PF1 inputs | Recompute all hashes, byte counts, schemas, row counts, query counts, eligible episodes, and exact query-cache hits |
| PF2 identity | Execute every named C0/T1 operation on all 25 real traces and verify Section 4's behavioral identity |
| PF3 ordering | Git ancestry and runtime sentinels prove design, authorization, Part 1, lock, and PF1-PF10 precede label parsing and measurement |
| PF4 reachability | Before output lock, verify every required fact has an eligible source; demonstrate every gate disposition on synthetic fixtures without using observed arm outcomes |
| PF5 stable keys | Source and span content hashes plus query-text SHA-256 only; generated IDs and paths never compare arms |
| PF6 reproduction | Reproduce all 24 M2 rank, selection, payload, character, and digest identities plus Q11 whole-episode baseline and BA-001's historical M2/M5 aggregate anchor |
| PF7 feedback | Prove C0/T1 are stateless by identity-equal repeated 25-query passes; no query-history absorbing state exists |
| PF8 adequacy | State that 25 frozen queries test one 121-turn lineage; a 35-turn prefix checks integration but cannot test turn-55 art or 120-turn efficacy |
| PF9 surrogate | Audit source-rank equality, span fidelity, packed facts, broad gain, no-loss, domain macro, budget, and ablation stability against false certification |
| PF10 live requirement | State that availability is not answer correctness; name the conditional 35-turn ablation and separately authorized full live comparison |

Every check cites an executed artifact. Prose-only assertions fail Preflight.

## 6. Sealed offline measurement and gates

Only a separate measurement module may parse the answer key, and only after a
committed passing Part 1 artifact, final-design lock, authorization, and
PF1-PF10 artifact exist. A fact is available only under its registered eligible
source turn, role, and required-term match in serialized payload bytes.

Stop at the first failed gate:

| Gate | Binding bar | Failure disposition |
|---|---|---|
| G1 integrity | Part 1 and PF1-PF10 pass; all C0 reproductions and cross-arm source ranks are exact | `INTEGRITY_STOP` |
| G2 matched retrieval and budget | C0/T1 full source identity and score sequences match for every query; both use the same eligibility and exact 32k ceiling | `RETRIEVAL_IDENTITY_MISMATCH` |
| G3 broad improvement | T1 Q11 packed fact count is at least C0 + 1, and T1 total packed matched facts across the 24 holdouts is at least C0 + 1 | `NO_BROAD_GAIN` |
| G4 zero targeted losses | Across all 24 paired holdout queries, T1 packed fact recall is never below C0; losses = 0 | `TARGETED_REGRESSION` |
| G5 no class/domain regression | Macro packed recall is non-decreasing for each of lookup, chained, and enumeration and for every required domain | `CLASS_OR_DOMAIN_REGRESSION` |

If G1-G5 pass, disposition is `SPAN_REPRESENTATION_OFFLINE_ELIGIBLE`. This is
availability evidence only. Art facts and art-domain recall are reported but
not separately required: art routing remains outside this one-component study.

Required outputs include paired rows for every query; Q11's 17 fact rows;
packed facts by class and domain; gains/losses/ties; whole/partial/absent T1
sources; selected unit/source counts; exact characters; and whether each gain
arose only because a source was partially packable. Candidate availability is
reported as the common full ranked population and is not allowed to certify a
delivery gain.

## 7. Conditional 35-turn ablation

The 35-turn ablation is authorized only after G1-G5 pass. Before inference, a
committed run lock must name exact runner SHA, server build hash, model, seed,
`--parallel 1`, disabled speculative decoding, prompt template, arm settings,
and a checked-out clean control worktree. Control may not be implemented by
flag-disabling T1 in the treatment runner.

The ablation uses scripted turns 1-35 plus a registered probe whose evidence is
mechanically planted in turns 1-34. It tests integration, exact budget charging,
source-rank identity, span provenance, leakage, state purity, and a byte-identical
seeded prefix rerun. It cannot estimate turn-55 art recovery or 120-turn answer
efficacy.

Both arms must complete, stay within 32k, reproduce offline identities for
matching queries, exclude future turns and forbidden files, preserve a clean
control boundary, and pass the prefix rerun. Failure is `ABLATION_FAILED`.
Passing is `READY_FOR_SEPARATE_LIVE_DECISION`; it does not authorize a full run.

## 8. Surrogate audit

| Observed pass | Property that can remain false | Control or residual |
|---|---|---|
| Same source ranking | Same delivered evidence | Paired serialized fact measurement |
| Faithful spans | Useful evidence retained | Exact required-term availability by source and role |
| More selected spans | More distinct facts | Fact identities, not counts |
| Q11 gain | Reader uses evidence | Separate live answer evaluation |
| Zero losses on 24 queries | General no-regression | One lineage and wording remain residual |
| Domain macro non-regression | Every query is safe | G4 separately requires zero per-query losses |
| Payload fits 32k | Equal delivered characters | Exact characters reported; only ceiling is matched |
| 35-turn ablation passes | 120-turn stability | Full-length run remains separately authorized |
| Span representation helps | Biological consolidation exists | Prohibited interpretation; no state or slow store exists |

## 9. Runtime, leakage, tests, and exclusions

Offline execution makes zero model-generation and zero new embedding calls.
The query cache is read-only. Set `OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`,
`MKL_NUM_THREADS=1`, and `NUMEXPR_NUM_THREADS=1`.

Component and Part 1 modules may not import or inspect answer keys, facts,
rubrics, scoring, prior measurement matrices, domains, span-vector caches, or
TA-001 neighbor outputs. Enforce source grep, AST import traversal, runtime open
sentinels, and a planted forbidden-path test. Measurement refuses to run before
all committed ancestors and passing artifacts exist.

Artifacts are UTF-8/LF canonical JSON or CSV, refuse overwrite, and include
commands, source hashes, manifests, and canonical digests. Tests cover sentence
boundaries, both roles, empty text, exact offset round trips, duplicate spans,
source-rank preservation, inherited scores, within-source order, partial-source
packing, skip-overflow continuation, exact 32k accounting, stable hashes,
forbidden paths, early measurement refusal, two-process determinism, C0 replay,
and every disposition.

SR-001 does not authorize span embeddings or reranking, salience filtering,
span deduplication, temporal adjacency, chaining, diversity floors, changed
budgets, label-aware selection, threshold changes after results, answer scoring,
a full live run, production adoption, or a claim of biological replication.

Closeout requires the pre-registration SHA in the report, committed artifacts
and manifests, README and AGENTS updates, retrieval-ledger and memory updates,
ERRATA review, full tests, a clean worktree, push, and a dedicated pull request.

---

*Registered prospectively on August 11, 2026 after the author merged TA-001 and
explicitly authorized the previously stated fixed-retrieval span study. This
file contains no SR-001 implementation or outcome.*
