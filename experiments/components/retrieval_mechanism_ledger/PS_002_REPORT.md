# PS-002 - Natural-Language Cue Binding to Sparse Engrams

**Pre-registration commit:** `e6b9c5cf6d54b1f5847c58b80f1764a2b6ea8086`
**Pre-registration SHA-256:** `79183A5A26C2BB88FDBEAFE36398D9B811720D71D024E8EF9C1AF533AD4411EC`
**Authorization commit:** `b535c66d`
**Implementation commit:** `5f972ee0`
**First-process artifact commit:** `cd4ff5e7`
**Determinism commit:** `3ed41b45`
**Date:** August 11, 2026
**Disposition:** `NATURAL_CUES_NOT_BOUND`
**Outcome ceiling:** `CHARACTERIZED`

## Outcome

PS-002 asked whether one label-blind semantic-to-engram binder could turn 24
sealed natural-language query vectors into eight safe stored PS-001 engrams per
query. It registered nine `(support width, temperature)` cells and required a
cell to complete all 192 query rounds without a cycle, runtime guard, spurious
terminal, duplicate output, or short output.

No cell passed that Part 1 mechanical gate. The strongest cell was:

```text
M = 4
TAU = 0.025
```

It reached stored PS-001 codes in `190/192` rounds. One round entered a cycle
and one converged to a spurious fixed point. Both occurred on sealed query
`h121_l02`, in rounds 3 and 4 under one-based numbering. That query emitted six
identities; the other 23 emitted eight. Because the gate required eight clean
identities for every query, no cell was eligible and no parameter cell was
selected.

The ordered disposition is `NATURAL_CUES_NOT_BOUND`. The study stops before the
final-design lock, PF1-PF10, answer-key parsing, relevance measurement, answer
generation, scoring, or a live run.

## Component behavior

The binder received only one normalized query embedding and the 119 normalized
episode embeddings and PS-001 codes. It computed cosine support over the store,
softmax-weighted the top `M` centered engrams, formed one exact 41-active cue,
ran unchanged PS-001 recurrence, emitted an identity only for an exact stored
terminal, inhibited that identity, and repeated for eight rounds.

The mechanism did not read source turns, domains, fact IDs, required terms,
rubrics, scores, or answer keys. It made zero embedding requests and zero model
generation calls.

The carried PS-001 memory reproduced exactly before every cell:

- committed mechanism digest
  `0D45DDD45980DBF3989A543136BAD52D4F743F650F3C0AF76E370F049B6C80CC`;
- code-sequence SHA-256
  `A8D1364A58DE6D6C70DB2DD771BA96E59FCF931D36CFB28EA69C780B55E3A3B8`;
- code-matrix SHA-256
  `E6EBFAB3FBEEC50A30784AB1161B7AECCE02BD33181A700F6A95CE43BBC9034A`;
- `119/119` stored fixed points.

## Nine-cell distribution

Each cell ran 24 queries for eight rounds, or 192 traces.

| Cell `(M, TAU)` | Stored | Spurious | Cycles | Duplicates | Changed and completed | Eligible |
|---|---:|---:|---:|---:|---:|---|
| `(4, 0.025)` | **190** | 1 | 1 | 0 | 76 | No |
| `(4, 0.050)` | 189 | 1 | 2 | 0 | 125 | No |
| `(4, 0.100)` | 189 | 1 | 2 | 0 | 151 | No |
| `(8, 0.025)` | 187 | 3 | 2 | 0 | 90 | No |
| `(8, 0.050)` | 178 | 5 | 9 | 0 | 143 | No |
| `(8, 0.100)` | 161 | 16 | 11 | 4 | 153 | No |
| `(16, 0.025)` | 181 | 6 | 3 | 2 | 86 | No |
| `(16, 0.050)` | 163 | 20 | 7 | 2 | 132 | No |
| `(16, 0.100)` | 120 | 33 | 20 | 19 | 115 | No |

Every cell had zero runtime guards. Wider or softer support mixtures caused
more cue changes but also substantially more spurious terminals, cycles, and
duplicate attractors. Recurrence activity was therefore not a surrogate for
safe binding.

## Strongest-cell traces

For `(4, 0.025)`:

- 114/192 cues were already stored fixed points and completed in one sweep;
- 76/192 cues changed and completed to stored identities;
- one cue changed 20 bits and entered a six-sweep two-cycle, with repeated-state
  witness `[4, 6]`;
- one cue changed 48 bits and converged in four sweeps to a spurious fixed point;
- initial-to-terminal Hamming distance had minimum 0, median 0, and maximum 48;
- sweep counts were 114 at one, 68 at two, five at three, four at four, and one
  at six;
- cue-field margins ranged from 0 through 0.9741, median 0.04080;
- semantic supports over all query/episode pairs ranged from -0.05492 through
  0.60128, median 0.14708;
- 53/119 stored engrams were emitted at least once; 66 were unused;
- emitted frequency among used engrams ranged from 1 to 9, median 3.

The repeated spurious terminal SHA-256 was
`7218969EB1A090AF851987C26B8E3F6798BE8C596004EA7D71E681A16F22094A`.
The cycle and spurious traces are retained with complete state, score, margin,
active-count, and repeated-state histories.

## Determinism and resources

Two fresh processes reproduced:

- mechanism digest
  `CFCA813A79EE96EE2949E9F567F9C5360ACB30D410E37AFD847EF65D5666E15C`;
- deterministic artifact-sequence digest
  `DF47BBBC1E6B7A21BB8EC48BF81D7661B494FD693EA0905A544874CA142D9194`;
- every canonical trace artifact byte-for-byte.

The first complete process took 7.87 seconds. Estimated live NumPy arrays were
9,793,536 bytes. Process RSS rose from 32,194,560 to 48,959,488 bytes, remaining
well below the registered 512 MiB limits.

The AST import audit passed and the planted forbidden mechanism path failed
loudly. The query cache reported 24 read-only 1,024-dimensional float32 vectors
from the pinned Qwen3 embedding model. No cache miss or model call occurred.

## Ordered stop

| Stage | Result |
|---|---|
| Pre-registration and authorization | PASS |
| Carried PS-001 identity | PASS |
| Part 1 complete nine-cell exploration | PASS |
| Two-process deterministic comparison | PASS |
| Mechanical cell eligibility | **FAIL - no eligible cell** |
| Final design lock | NOT REACHED |
| PF1-PF10 | NOT REACHED |
| Relevance labels and G1-G5 | NOT REACHED |
| Chained/enumeration stress tests | NOT REACHED |
| Answer generation and scoring | NOT AUTHORIZED |
| Live evaluation, promotion, adoption | NOT AUTHORIZED |

The failure occurs before PF1-PF10 because the pre-registration makes a viable
label-blind selected cell the entry condition for Part 2. The answer key was not
opened by PS-002 measurement code, and no PS-002 relevance number exists.

## Interpretation

PS-001's source-centered basins do not automatically accept semantic mixtures.
When one episode dominates, most sharp cues are already exact stored codes. As
the cue becomes more genuinely mixed, recurrence often changes it, but those
changes increasingly fall into a small set of spurious or cyclic states rather
than reliably separating eight clean memories.

This closes one gap and exposes the next one precisely:

- stable sparse engrams exist;
- natural language can often drive the network to stored engrams;
- the registered multi-output binder cannot guarantee a safe eight-item set;
- more recurrence is not evidence of more relevant or safer binding;
- relevance and answer-score effects remain unknown.

The result must not be summarized as 98.9% cue-binding success. That fraction
counts stored terminal rounds, while the certified property was a complete safe
output for every query. The strongest cell fails that property.

## Advancement

PS-002 does not authorize a live answer run. A next design would need a new
prospective mechanism for handling ambiguous or mixed cues, with explicit
spurious/cycle rejection that does not silently fall back to cosine retrieval.
It must also decide whether one attractor should represent one memory or whether
multi-memory questions require a different architecture. Those are new design
choices, not amendments to this stopped study.

## Evidence

- Design: `PS_002_NATURAL_LANGUAGE_CUE_BINDING.md`
- Authorization: `PS_002_AUTHORIZATION.md`
- First process: `artifacts/ps002_exploration/part1_process_1/exploration.json`
- Cell summary: `artifacts/ps002_exploration/part1_process_1/cell_summary.csv`
- Complete traces: `artifacts/ps002_exploration/part1_process_1/cells/*/traces.jsonl`
- Artifact manifest: `artifacts/ps002_exploration/part1_process_1/artifact_manifest.json`
- Two-process comparison: `artifacts/ps002_exploration/two_process_determinism.json`

## ERRATA review

No previously published number changes. `ERRATA.md` is unchanged.
