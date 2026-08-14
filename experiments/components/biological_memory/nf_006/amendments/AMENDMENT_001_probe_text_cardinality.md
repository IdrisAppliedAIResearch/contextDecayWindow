# NF-006 Amendment 001 - Probe Text Cardinality

**Status:** `AUTHORIZED - PRE-CAPTURE`
**Authorization:** user instruction in the NF-006 execution thread, August 13,
2026
**Applies to:** `NF_006_PRE_REGISTRATION.md` at commit
`ebb3ebf3d103e7ceaa62576879e0825fbfc11ee1`
**Trigger:** PF2/PF6 reconciliation before vector capture

## 1. Trigger and committed evidence

Section 5 of the locked registration says the probe-vector call contains nine
unique texts. The carried internal path has eight unique probe texts. This is
not a new observation or a changed population; it is already fixed in the
following committed records:

- IC-001 reports eight committed targeted questions and records the unique
  selection prefixes `112, 113, 115, 116, 117, 118, 119, 120` in
  `runs/ic001/b1_k_first/b1_arm.json`. The report is at
  `b479d8feb659de29e5b744a51e61502b61305c4b`; the arm and targeted matrices are
  at `4947582e54a44af20610d8cd801878a3c9a7254e`.
- NF-001 publishes two eight-probe streams in `NF_001_PART1_RECORD.md` and its
  record at `d8f5fd924679464ae8234a00d8c257aee9b996fb`.
- E006 Part 2 publishes the same eight probe turns and their query SHA-256 map
  in `artifacts/e006_part2_preflight/preflight.json` at
  `3f6bcb1bfed11e53e387f7ca803d181b85a50dc3`.
- E006 Part 3 records targeted-vector coverage as `0/8` in
  `artifacts/e006_p3_preflight/preflight.json` at
  `81299313236a5302a3a68e135d42779596765944`.

The E006 Part 2 query map is the cardinality anchor: it contains eight distinct
SHA-256 values, one for each listed turn. Q7 and Q10 both use turn 118 and
therefore share one query text, one query vector, one eligible pool, and one
selection. Q11 adds turn 120 to the seven unique targeted turns.

## 2. Corrected quantities

These quantities are separate and must not be conflated:

| Quantity | Correct value | Population effect |
|---|---:|---|
| Unique probe texts and query vectors | **8** | Corrects only Section 5's call cardinality |
| Scored probe labels, including Q11 | **9** | Unchanged: Q1, Q2, Q4-Q8, Q10, Q11 |
| Targeted scored probe labels | **8** | Unchanged |
| Unique selection prefixes, including Q11 | **8** | Unchanged |
| Q11 breadth items | **17** | Unchanged |
| Targeted scored item rows | **21** | Unchanged |
| Total scored item rows | **38** | Unchanged |

Q7 and Q10 do **not** collapse into one scored outcome. They share the turn-118
selection, but remain separate scored probes: Q7 has five item rows and Q10 has
two. The two Q10 items also occur in Q7, as they did in the committed IC-001
matrix. No probe and no scored row is dropped, added, merged, or reweighted.

## 3. Change

Replace the Section 5 execution instruction conceptually, without editing the
locked registration:

> Probe vectors reproduce the committed internal path exactly: the eight
> unique probe texts at turns 112, 113, 115, 116, 117, 118, 119, and 120 are
> sorted lexicographically and embedded in one eight-text batch.

All references to the registered probe-vector cardinality are interpreted
through this amendment. No other registration text changes.

## 4. Frozen-path verification against IC-001

The pre-capture audit reproduced these committed-path properties:

| Property | Verification |
|---|---|
| Turn list | IC-001 `b1_arm.json` has exactly `112,113,115,116,117,118,119,120`; every stored `probe_turn` agrees with its key |
| Query identity | The hash-locked turns log yields eight texts and eight distinct text SHA-256 values; their ordered digest is `e106c61cfd635ff2419e49b2f748338fb3219216c7906bf85ea659343e89c90b` |
| Targeted grain | IC-001 has eight separately keyed targeted rows and 21 distinct `(question, turn, item)` rows; Q7/Q10 share two item strings but retain separate question keys |
| Corpus identity | IC-001 source integrity locks `study.db` to `5da47ea3fc2c8e3dcc50fa380ff65202d82557905d9976117e9e5d82e55c1c41`, identical to NF-006 |
| Episode population | The locked database has 121 rows and exactly 119 episodes eligible before turn 120 |
| IC-001 references | All 80 selected-id occurrences, 59 unique ids, resolve in the locked database; source-turn mismatches are `0` |
| NF-006 C0 anchor | E005's committed 15 ids all resolve in the same IC-001-locked database; ordered id digest `4b9709cb0a43672972a0dc72e3dc2f16cf57707c6cf07036dfd01891ea2da99d`, turns `114,43,1,2,78,110,27,3,54,84,118,113,115,112,116` |

The E005 C0 source is `artifacts/e005/raw/q11_selection.jsonl` at
`cf0df29187321a1d8d58bb171d68a4b5f98781c1`, file SHA-256
`71d7d1a6f4d46d231a0ddd3ee11bea285f659456707f0754cae211d992dba9b7`.
Its payload SHA-256 remains
`a1ecbee8e77d685ee4706767cba5ccab8bac44d7f24551b94ebd0aad20ca8f98`
at 31,569 characters.

## 5. PF4 reachability after correction

The corrected `n=8` changes only vector-call cardinality. Effect on every
registered gate and result bar:

| Gate or bar | Reachability at corrected n | Effect |
|---|---|---|
| G0 registration | Registration plus this authorized standalone amendment can be commit-verified | No threshold change |
| G1 frozen inputs | Eight query hashes, 119 eligible episodes, 791 statements, and all locked files are countable | Query count `9 -> 8`; no other count changes |
| G2 leakage | Static and planted violations are independent of query count | None |
| G3 C0 Q11 anchor | 15 ids, 12/17, 4/4, 31,569 chars, and payload SHA remain committed and reachable | None |
| G3 targeted anchors | Eight scored labels and 21 item rows remain available from seven targeted selections | No scored-population change |
| G4 statement identity | 119 parents and 791 statements are independent of query count | None |
| G5 vector seal | Exactly 8/8 probe vectors and 791/791 statement vectors can be sealed; parent cosine tolerance remains `1e-7` | Probe-vector cardinality only |
| G6 deterministic replay | Each pass runs three arms at eight unique prefixes; Q7/Q10 reuse the same turn-118 result | Removes one duplicate computation; coverage unchanged |
| G7 selection seal | Seals 24 unique arm/prefix records per pass (`3 x 8`) before either key opens | Record count reflects unique selections, not scored labels |
| G8 item losses | Zero losses among 21 targeted rows remains reachable in the equality case | None |
| G8 total availability | T1 not below C0 over 21 rows remains reachable in the equality case | None |
| G8 per-probe bar | No lower result across eight targeted labels remains reachable; Q7/Q10 are both scored from the shared payload | None |
| G8 per-domain bar | No domain lower remains reachable in the equality case | None |
| G9 Q11 breadth | `14/17` remains mechanically reachable at the committed 5,058-character oracle cost | None |
| Positive disposition T1 > C1 | Independent of query cardinality | None |
| Positive disposition monetary gain | At least one of four registered monetary items can differ | None |
| Packing-only disposition C1 > C0 and T1 <= C1 | Independent of query cardinality | None |
| Integrity-stop fireability | Each named stop still has a synthetic failing input | None |

Thus no result bar becomes easier or harder. The only numerical execution
change is one eight-text probe batch and 24 unique arm/prefix selections rather
than a falsely implied nine-text batch or 27 unique selections.

## 6. Rationale and exclusions

This amendment repairs an internal cardinality contradiction before capture and
restores the already published call shape. It does not respond to an NF-006
result; no NF-006 capture, selection, availability measurement, or disposition
has run.

It does not change the splitter, statement population, query text, turn list,
eligible pools, candidate identities, episode identities, cluster assignments,
selector, budget, serializer, call ordering, scoring grain, any gate, any bar,
or any disposition. It does not authorize probe deduplication in measurement:
Q7 and Q10 remain separate scored probes exactly as committed in IC-001.
