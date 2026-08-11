# TA-001 - Temporal-Adjacency Bridge Retrieval

**Type:** Pre-registered offline component study with conditional 35-turn ablation
**Date:** August 11, 2026
**Branch:** `study/ta-001-temporal-adjacency-bridge`
**Status:** PRE-REGISTERED - IMPLEMENTATION AND OUTCOME ACCESS PROHIBITED UNTIL AUTHORIZATION
**Predecessor:** BA-001 benchmark causal audit
**Outcome ceiling:** `CHARACTERIZED`; no production adoption or full live run

## 1. Question and scope

BA-001 showed that E006 chaining did not discover more Q11 facts than a
matched fixed-query retrieval. At 15 candidates, both held 9/17 candidate
facts; chaining packed 9/17 rather than 7/17. BA-001 also established an
unmeasured opportunity: both matched candidate sets contain source turn 54,
which is immediately adjacent to turn 55, the episode containing all four
missing art facts.

TA-001 adds exactly one component: a deterministic temporal-adjacency bridge.
It asks:

> When a label-blind direct-query seed is retrieved, does admitting its
> immediately preceding and following stored turns recover broad evidence
> without sacrificing targeted evidence under the same candidate quota and
> character ceiling?

The component is motivated by the sequential-connectivity distinction in
`HYPOTHETICAL_001_MECHANICAL_BIOLOGICAL_MEMORY_MODEL.md`, especially P4 and
Section 5. It is not an implementation or validation of biological replay.
There is no learned edge, salience capture, accessibility state, consolidation,
or retrieval plasticity in TA-001.

## 2. Immutable inputs

Every input is verified by byte count and SHA-256 before execution. A mismatch
stops the study.

| Input | Bytes | SHA-256 |
|---|---:|---|
| Root biological-memory reference | 17,505 | `DBC6A1C4134DF37877D6F5A77ACDF61DB4CE8361A1F7B2A2810B6182A6D6F926` |
| BA-001 report | 6,861 | `EFAA03B10A90DA68C7F284BB092A80D1EDBBB724A84D871CB89A5E4A4A18D14C` |
| BA-001 results | 41,619 | `1C0D6FB6EF01E991FD7F14EBBA2900D0770325C564B64648B9D716A84E1630F1` |
| E006 P3 result | 741,804 | `5A6B8A6731B813E0BF63071838D1B14CEAF41362D6548C0BCED9777E2BBE49EF` |
| E006 P3 fixed-query source | 7,858 | `8BB02F16DD6D07CDA0D050289DAB6AB939E9CF7048D14564B8E71DFBD3347030` |
| Q11 119-episode rank inventory | 10,642 | `8D6F9EEE6EBE232608981AAC0C0D4816EAEC4710AE551DB028AE0B323253AC03` |
| 121-turn episode database | 1,978,368 | `5DA47EA3FC2C8E3DCC50FA380FF65202D82557905D9976117E9E5D82E55C1C41` |
| Sealed 24-query manifest | 4,231 | `AE950FDA20DCE9F519F31EE2670A815A5599648CAB618D42309DB7E3F23D36F4` |
| Read-only `c121_l` vector cache | 13,164,544 | `A58EE1163D3C2417962B1FCC4AB84DC4EDC313C8254A967376A59558EE28A45D` |
| Measurement-only answer key | 9,832 | `2D43A31D3C04F4AD690FF2910ABDE71F508A3F6CE776545A9F2B16F90FAE5320` |
| Authoritative packer | 5,164 | `C5011DADA056FA0106544925C75D849C3D5B4857B6C5010ED4B604F9C3D2AF04` |
| Authoritative renderer | 2,022 | `D0BDC051695FE98064BAD9ECC52AFE0178BBA1BA8A3EDF7E3A1960D5F261CF6F` |

The Q11 population is exactly source turns 1-119. Each holdout query uses
exactly source turns 1-111, as sealed in the query manifest. Episodes are
identified across arms only by a canonical SHA-256 of turn number, user text,
and assistant text. Generated database IDs are never comparison keys.

The answer key is measurement-only. Part 1 and component code may verify its
file hash but may not parse, import, or inspect it.

## 3. Arms and fixed parameters

The following parameters are authoritative and are not swept:

```text
CANDIDATE_QUOTA = 15
TEMPORAL_RADIUS = 1
BUDGET_CHARS = 32000
Q11_ELIGIBLE_TURNS = 1..119
HOLDOUT_ELIGIBLE_TURNS = 1..111
TIE_BREAK = ascending episode content SHA-256
NEIGHBOR_TIE_BREAK = ascending episode content SHA-256
```

### 3.1 C0 - fixed-query control

Rank every eligible episode by descending cosine to the query, breaking exact
ties by content SHA-256. Admit the first 15 unique episodes in that order. Pack
that ordered list with the authoritative skip-overflow packer and a 32,000
character ceiling.

For Q11, the committed rank inventory is authoritative. C0 must reproduce the
E006 P3 A0 `D=2,m=5` 15-candidate identity sequence and its packed payload
identity exactly before any new result is opened.

### 3.2 T1 - temporal-adjacency bridge

Use the complete C0 ranking as the seed stream. Iterate seeds in rank order.
For each seed not already admitted:

1. Admit the seed.
2. Resolve stored episodes at source turns `seed.turn - 1` and `seed.turn + 1`.
3. Remove ineligible and already admitted episodes.
4. Order the remaining immediate neighbors by content SHA-256 and admit them.
5. Stop immediately when 15 unique candidates have been admitted.

If the quota is not full, continue to the next direct-query seed. A bridged
neighbor is not recursively expanded. The ordered candidate list is the
admission order. Pack it with the same packer and 32,000 character ceiling as
C0.

The mechanism may read query vectors, episode vectors, source turns, and
episode content hashes. It may not read domains, fact IDs, required terms,
rubrics, prior selected source turns, or measurement outcomes.

## 4. Part 1 - label-blind empirical characterization

Part 1 runs C0 and T1 on 25 committed queries: Q11 and all 24 sealed holdout
queries. It does not open the answer key or count facts.

For every query and arm, retain:

- complete direct-query seed rank and content-hash sequence;
- ordered 15-candidate identities and source turns;
- for each T1 admission, role (`seed`, `previous`, or `next`), parent seed
  identity and rank, temporal distance, and dedup reason if skipped;
- candidate overlap, displaced C0 seed ranks, seed/neighbor admission counts,
  direct-rank distribution of admitted neighbors, and turn-distance
  distribution;
- serialized candidate characters, packed identities, selected count,
  skipped identities, delivered characters, and payload digest;
- boundary events, duplicate collisions, quota truncations, and any query that
  emits a constant or repeated prefix;
- zero embedding requests, zero generation calls, process metadata, source
  hashes, and a manifest of every artifact.

Part 1 must be repeated in a fresh process. Deterministic artifacts, excluding
explicit process metadata, must have the same canonical digest.

### 4.1 Behavioral identity

The falsifiable identity is:

> T1 emits exactly 15 unique eligible episodes by interleaving each unseen
> direct-query seed with only its stored radius-1 temporal neighbors, without
> labels, recursion, or a larger packing budget.

### 4.2 Part 1 eligibility

All conditions must pass to continue:

1. C0 and T1 emit exactly 15 unique candidates for all 25 queries.
2. Every T1 neighbor has absolute source-turn distance exactly one from its
   recorded parent seed and precedes the probe.
3. Every T1 seed preserves the direct-query order among admitted seeds.
4. Every payload is at most 32,000 characters under the authoritative packer.
5. Q11 C0 reproduces the committed A0 candidate, packed-identity, and payload
   digests exactly.
6. Two fresh processes produce identical deterministic digests.
7. Forbidden-label import, path, and runtime sentinels all stop loudly.

Failure disposition is `BRIDGE_MECHANICS_INVALID`; stop before Part 2 labels.

## 5. Final design lock

After Part 1 is committed, a standalone final-design file must bind:

- the Part 1 commit and deterministic digest;
- the unchanged T1 policy and parameters in Section 3;
- the exact C0 reproduction identities;
- Part 1 eligibility;
- whether Part 2 is authorized to proceed.

The final-design lock may not report required facts, domains, answer-key source
turns, recall, gains, losses, or art outcomes. It is committed before Part 2
measurement code may run.

## 6. Preflight

Preflight has two ordered parts. Section 4 is Part 1. After its commit and the
final-design lock, Part 2 executes PF1-PF10 before measurement.

| Check | Required executed evidence |
|---|---|
| PF1 inputs | Hash, bytes, schema, row count, vector dimensions, eligible-turn count, and exact cache hit for all 24 query texts |
| PF2 identity | Execute every named operation in C0 and T1 on all 25 real traces and verify Section 4.1 |
| PF3 ordering | Git ancestry plus runtime sentinels prove design, authorization, Part 1, final lock, and PF1-PF10 precede label parsing and measurement |
| PF4 reachability | Before lock, verify all required facts have at least one eligible source and compute ceilings of 17/17 Q11, 4/4 Q11 art, and complete holdout requirements; no observed arm output is used |
| PF5 stable keys | Content SHA-256 and query-text SHA-256 only across arms and processes |
| PF6 reproduction | Reproduce Q11 C0's committed 15 candidates, packed identities, payload bytes, 7/17 packed facts only after labels open, and all registered Tier 2 input aggregates |
| PF7 feedback | Record that C0 and T1 are stateless within and across queries; prove a repeated 25-query pass is identity-equal and cannot enter a query-history absorbing state |
| PF8 adequacy | State that 25 queries test this 119-episode lineage; a 35-turn prefix can detect integration, budget, leakage, and determinism failures but cannot test turn-55 art recovery or 120-turn endurance |
| PF9 surrogate | Audit candidate count, neighbor count, broad facts, art facts, targeted no-loss, payload size, and ablation stability against the properties they can fail to certify |
| PF10 live requirement | State that offline availability is not answer correctness; name the conditional 35-turn ablation and separately authorized 121-turn live answer comparison |

Every check must cite an executed artifact. Checked boxes or prose-only claims
fail Preflight.

## 7. Sealed offline measurement

Only after Part 1, final design lock, authorization, and passing PF1-PF10 may a
separate measurement module parse the answer key.

A fact is available only under the answer key's registered source-turn and
required-term match against one serialized episode. Report candidate and packed
availability separately for every fact, query, class, and domain.

### 7.1 Ordered gates

Stop at the first failure.

| Gate | Binding bar | Failure disposition |
|---|---|---|
| G1 integrity and reproduction | All Part 1 and PF1-PF10 checks pass; Q11 C0 identity exact | `INTEGRITY_STOP` |
| G2 matched opportunity | Both arms emit 15 candidates for every query; every payload is at most 32,000 chars; same packer and representation | `UNMATCHED_OPPORTUNITY` |
| G3 broad discovery | T1 candidate Q11 facts are at least C0 + 1 and T1 packed Q11 facts are at least C0 + 1 | `NO_BROAD_GAIN` |
| G4 art recovery | T1 candidates contain 4/4 Q11 art facts and the T1 packed payload contains 4/4 | `ART_NOT_DELIVERED` |
| G5 targeted no regression | Across all 24 holdout queries, T1 packed fact recall is never below C0; total losses = 0; each query class and required domain is non-decreasing | `TARGETED_REGRESSION` |

If G1-G5 pass, the offline disposition is
`ADJACENCY_BRIDGE_OFFLINE_ELIGIBLE`. This is availability evidence only.

### 7.2 Required reports

Retain a paired row for every query with candidate and packed facts, source
identities, delivered characters, gains/losses/ties, query class, and required
domains. For Q11 retain all 17 fact rows and the four art rows. Report whether
any gain comes from candidate discovery, ordering/packing, or both.

## 8. Conditional 35-turn ablation

The 35-turn ablation is authorized only if G1-G5 pass. Before inference, commit
a calibrated run lock containing the exact runner SHA, server build hash,
model, seed, `--parallel 1`, no speculative decoding, prompt template, and arm
configuration. The ablation uses a checked-out control worktree and may not be
implemented by disabling T1 in the treatment runner.

The ablation runs the first 35 scripted turns plus a registered turn-35 probe
whose required evidence is mechanically verified to occur in turns 1-34. It
tests integration, exact budget enforcement, retrieval identity logging,
label leakage, state purity, and a byte-identical seeded prefix rerun. It does
not estimate the turn-55 art effect or answer-quality efficacy.

Binding ablation gates:

1. Both arms complete 35 turns and the probe without an error.
2. Every serialized memory block is at most 32,000 characters.
3. Candidate and payload logs reproduce offline identities for matching
   queries and contain no future turn.
4. The seeded prefix rerun is byte-identical through the registered prefix.
5. The control worktree has the expected commit, module paths, source hashes,
   clean status, command, server properties, and PID.
6. No rubric or answer-key path is opened by either retrieval mechanism.

Failure disposition is `ABLATION_FAILED`. Passing disposition is
`READY_FOR_SEPARATE_LIVE_DECISION`; it does not authorize a 121-turn run.

## 9. Surrogate audit

| Observed pass | Property that can remain false | Required control or residual |
|---|---|---|
| Fifteen candidates per arm | Equal semantic opportunity | Per-fact and per-domain paired measurement |
| Neighbor admitted | Useful evidence discovered | Required-term match after sealed identities |
| Q11 facts increase | Reader uses them | Separate live answer study required |
| Art appears in candidates | Art reaches the prompt | G4 requires packed 4/4 separately |
| Art reaches the prompt | The answer is correct and non-fabricated | Live reader scoring remains required |
| Zero targeted losses on 24 queries | General no-regression | Single lineage and wording remain residual limits |
| Payloads fit 32k | Equal delivered volume | Report exact characters and selected counts; only the ceiling is matched |
| 35-turn ablation passes | 120-turn behavior is stable | Full-length evaluation remains separately authorized |
| Temporal adjacency helps | Biological replay is implemented | Explicitly prohibited interpretation |

## 10. Runtime and leakage

Part 1 and offline measurement make zero model-generation calls and zero new
embedding calls. Use the sealed vector cache read-only. Set
`OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, and
`NUMEXPR_NUM_THREADS=1`.

Component and Part 1 modules may not import or inspect answer keys, fact files,
rubrics, scoring modules, prior measurement matrices, or domain labels. Enforce
the boundary by source grep, AST import traversal, runtime open sentinels, and a
planted forbidden path test. Measurement code is separate and refuses to run
without a committed passing Part 1 artifact, final design lock, authorization,
and PF1-PF10 artifact.

Artifacts use UTF-8, LF newlines, canonical sorted JSON, overwrite refusal,
explicit source hashes, commands, environment, elapsed time, RSS, and SHA-256
manifests.

## 11. Tests and closeout

Unit tests must cover direct-query tie order, boundary turns, missing turns,
duplicate neighbors, seed-neighbor collisions, no recursive expansion, exact
quota stop, ineligible future exclusion, pack skip-overflow behavior, stable
hash identities, forbidden paths, early measurement refusal, two-process
determinism, and every disposition.

Closeout requires the pre-registration SHA in the report, all artifacts and
manifests committed, README and AGENTS digest updates, retrieval-ledger and
memory updates, ERRATA review, full tests, a clean worktree, push, and one
dedicated pull request.

## 12. Explicit exclusions

TA-001 does not authorize:

- changing candidate quota, radius, admission order, representation, packer,
  budget, gates, or thresholds after Part 1 or measurement;
- span extraction, learned graph edges, chaining, pattern-separated codes,
  salience, consolidation, accessibility, suppression, or supersession;
- label-aware selection, source-turn targets, domain floors, or oracle repair;
- a 121-turn inference run, answer-score promotion, production adoption, or a
  claim of biological replication.

---

*Registered prospectively on August 11, 2026 after the author merged PS-002,
PS-003, and BA-001 and explicitly requested the temporal-adjacency bridge study.
Implementation requires a standalone authorization bound to this committed
design.*
