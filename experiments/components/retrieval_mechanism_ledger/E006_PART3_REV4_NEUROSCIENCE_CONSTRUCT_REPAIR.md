# E006 Part 3 Rev 4 - Autoassociative Construct Repair

**Type:** Prospective post-result repair protocol
**Identifier:** `E006-P3-R4`
**Branch:** `study/e006-p3-query-anchored-associative-frontier-retrieval`
**Status:** PRE-REGISTERED - IMPLEMENTATION REQUIRES STANDALONE AUTHORIZATION
**Calls:** zero embedding requests; zero model-generation calls
**Outcome ceiling:** `CHARACTERIZED`, regardless of result
**Immutable prior result:** `E006_PART3_REPORT.md` at commit `d1d9689f`

This revision does not amend, replace, or reinterpret the completed E006 Part 3
result. That result remains a valid negative test of local propagation over an
exact-cosine episode graph. Rev 4 prospectively repairs a construct-validity
failure exposed after closeout: the tested mechanism was called associative,
but it did not implement learned recurrent attractors or pattern completion.

The program author stated that the intended property was replication of the
neuroscience and authorized an amendment and reimplementation. Authorization
must be bound to the committed SHA and content hash of this document before any
implementation file is added.

---

## 1. Trigger and integrity boundary

E006-P3 formed an undirected top-8 graph from dense episode cosine and selected
new nodes with a convex sum of query cosine and the maximum edge from the prior
frontier. It had no encoding-time association, plastic recurrent weights,
stored attractor, convergence dynamics, or partial-cue recovery test. It was a
semantic-neighborhood walk.

The failure is mechanical rather than a negative neuroscience result. Classical
content-addressable memory requires collective recurrent dynamics that recover
a stored state from a subpart or degraded state. CA3 lesion and circuit studies
likewise distinguish partial-cue pattern completion from generic semantic
similarity, and human event-completion work tests reinstatement of associated
elements within a coherent event:

- Hopfield (1982): https://pubmed.ncbi.nlm.nih.gov/6953413/
- Nakazawa et al. (2002): https://pubmed.ncbi.nlm.nih.gov/12040087/
- Guzman et al. (2016): https://pubmed.ncbi.nlm.nih.gov/27609885/
- Leutgeb et al. (2007): https://pubmed.ncbi.nlm.nih.gov/17303747/
- Horner et al. (2015): https://www.nature.com/articles/ncomms8462

Rev 4 tests a narrower claim than "replicates the hippocampus": whether a
canonical autoassociative recurrent memory can store the committed episode
patterns as attractors and recover them from degraded cues. It does not claim
biophysical realism, dentate-gyrus pattern separation, temporal sequence
learning, systems consolidation, or executive multi-memory search.

The original `NO_DIFFERENTIATED_CUE` disposition, thresholds, predictions,
artifacts, report, and ledger record are immutable. Rev 4 receives a separate
identifier, artifacts, result, and report. No Rev 4 result can rescue or change
the E006-P3 result.

---

## 2. Question

> On the committed 119-episode Q11 store, does a deterministic Hebbian
> autoassociative network make every encoded episode a stable attractor and
> recover its exact attractor from a deterministic one-bit-degraded cue?

This is the binding construct question. Only after it passes may the repair run
a descriptive Q11 translation probe.

Q11 asks for facts from four separate domain memories. Pattern completion
normally completes one coherent memory from a partial cue; it does not by
itself implement executive enumeration across several unrelated attractors.
Therefore Q11 breadth is not the primary construct test and cannot overturn a
failed attractor gate.

---

## 3. Single repaired component

The single new component is `EpisodeAutoassociativeMemory`. Existing episode
texts, content hashes, eligibility, cached normalized vectors, compact renderer,
and exact 32,000-character packer are carried unchanged. The old cosine graph
and frontier operator are not used by this component.

### 3.1 Pattern encoding

Let `X` be the carried matrix of normalized episode vectors, with 119 rows and
carried vector dimension `p`. For each coordinate `j`, compute the median
`c_j` across all eligible episode rows. Encode episode `i` as:

```text
xi[i, j] = +1 if X[i, j] >= c[j], otherwise -1
```

The same committed median vector encodes any query vector. This deterministic,
parameter-free centering balances coordinate activity where the data permit;
it is not called biological pattern separation. Content SHA-256 is the episode
identity. Duplicate bipolar patterns fail before network construction.

### 3.2 Learned recurrent weights

With patterns as rows of `Xi`, construct the symmetric Hebbian matrix:

```text
W = (Xi.T @ Xi) / p
diag(W) = 0
```

No cosine graph, nearest-neighbor edge, answer key, rubric, source turn, domain,
or Q11 fact label enters `W`.

### 3.3 Recall dynamics

Recall starts from a bipolar cue state `s`. Each sweep updates coordinates in
ascending index order, immediately exposing each update to the remaining
coordinates:

```text
field = dot(W[j, :], s)
s[j] = +1 if field > 0
s[j] = -1 if field < 0
s[j] = previous s[j] if field == 0
```

Stop at the first full sweep with no changed coordinates or after `p` sweeps.
The latter is a runtime guard, not a successful convergence state. Record the
Hopfield energy after every sweep:

```text
E(s) = -0.5 * s.T @ W @ s
```

Successful asynchronous recall must converge to a fixed point and have a
non-increasing energy trace. The implementation must detect repeated states,
although a repeated non-fixed state is a gate failure.

### 3.4 Deterministic degraded cues

For each episode content hash, derive a permutation of the `p` coordinates from
SHA-256 in counter mode. Flip the first `k` unique coordinates for each level:

- Binding level: `k = 1`.
- Descriptive levels: `k = floor(0.10 * p)`, `floor(0.30 * p)`, and
  `floor(0.50 * p)`.

The corruption function, counter serialization, and expected coordinate lists
must be unit tested and committed before any recovery result is generated.

---

## 4. Ordered gates and disposition

The following gates execute in order. A failure stops before later stages.

### G1 - Input and encoding integrity

- Exactly 119 eligible episodes and their carried vectors reproduce by content
  identity and matrix digest.
- Every vector is finite and has the same carried dimension.
- Bipolar encoding contains only `{-1, +1}` and has 119 unique rows.
- Leakage grep, import-graph check, and planted forbidden-import test pass.

### G2 - Weight and dynamics identity

- `W` is byte-reproducible, symmetric, finite, and exactly zero on its diagonal.
- An independent slow reference reproduces fields, updates, energies, terminal
  states, and convergence status on committed fixtures.
- Every completed sweep has non-increasing energy; any increase fails.

### G3 - Stored-attractor gate

Starting from each uncorrupted `xi`, all `119/119` states must remain unchanged
after one full sweep and be reported as fixed points. This exact bar is
structurally achievable: a network that stores the registered patterns as
attractors reaches it. Failure disposition: `PATTERNS_NOT_STORED`.

### G4 - Minimal pattern-completion gate

Starting from each deterministic one-bit-degraded cue, all `119/119` recalls
must converge to the exact source pattern. Exact recovery is compared by full
pattern bytes and content hash, not nearest-neighbor identity. Failure
disposition: `NO_EXACT_MINIMAL_COMPLETION`.

The `10%`, `30%`, and `50%` levels report the full per-episode distribution of
terminal identity, Hamming distance, sweeps, energy change, convergence,
wrong-attractor convergence, and spurious fixed points. They do not rescue or
kill the binding result.

### G5 - Degenerate-cue audit

Run all-`+1`, all-`-1`, alternating-sign, and four content-hash-seeded random
cues. Record whether each converges, its terminal pattern hash, whether it is a
stored attractor, and basin duplication. No favorable interpretation may omit
spurious or dominant attractors.

### Binding disposition

| First failure or completion | Rev 4 disposition |
|---|---|
| G1 or G2 fails | `INVALID_IMPLEMENTATION` |
| G3 fails | `PATTERNS_NOT_STORED` |
| G3 passes and G4 fails | `NO_EXACT_MINIMAL_COMPLETION` |
| G3 and G4 pass | `AUTOASSOCIATIVE_COMPLETION_DEMONSTRATED` |

Every valid disposition remains `CHARACTERIZED`. No parameter search, alternate
encoding, weight modification, pseudoinverse rule, capacity reduction, episode
filtering, or threshold relaxation is authorized after a gate result is seen.
Any such change requires a new prospective revision.

---

## 5. Descriptive Q11 translation probe

G1-G4 must pass before this probe can execute. Encode the carried Q11 query with
the committed median, run the same recurrence, and rank all stored patterns by
descending normalized bipolar overlap with the terminal state:

```text
overlap(xi, s) = dot(xi, s) / p
```

Ties break by ascending content SHA-256. Decode the top 15 episode identities,
then pass them through the unchanged compact renderer and exact 32,000-character
packer. Report terminal convergence, terminal stored-attractor identity if any,
all 119 overlaps, top-15 identities, packed payload digest, exact characters,
and Q11 fact/domain availability.

This probe is descriptive. It may say whether one completed basin retrieves a
useful episode neighborhood. It may not claim that a single-attractor mechanism
should solve four-memory enumeration, may not compare itself as a promotion
candidate, and cannot change the binding Rev 4 disposition.

If G3 or G4 fails, no Q11 fact key is imported and no translation score is
produced.

---

## 6. Preflight Part 1 - required exploration

Exploration runs after this design and its authorization are committed but
before the final PF1-PF10 artifact, evidence runner, or fact-key import exists.
It produces no Q11 fact counts.

Required committed outputs:

1. A falsifiable behavioral identity sentence based on executing the repaired
   component on all 119 uncorrupted patterns and all deterministic degraded
   cues.
2. Name-to-behavior checks for `pattern`, `Hebbian`, `recurrent`, `attractor`,
   `fixed point`, `pattern completion`, `energy`, `basin`, and `decoder`.
3. Full distributions, not only means, for pattern balance, pairwise Hamming
   overlap, stability, recovery, sweeps, terminal distance, and energy change.
4. Real traces for at least one stored pattern, one one-bit cue, one 30% cue,
   every degenerate cue, every non-convergent state, and every spurious or
   wrong-attractor terminal class.
5. Mechanical comparison showing the repaired component is not a relabeling or
   monotone transform of E006-P3's cosine graph/frontier ranking.
6. A construct table separating demonstrated properties from omitted neural
   commitments and separating one-memory completion from multi-memory search.

Exploration may discover that the fixed design fails G3 or G4. That is a valid
mechanistic result, not permission to tune. The exploration artifact records
the failure and the run stops before Q11 measurement.

---

## 7. Preflight Part 2 - PF1-PF10

Each item must name a committed artifact and executed test. Checked boxes and
assertions are insufficient.

| ID | Required answer before evidence |
|---|---|
| PF1 | Hash and count the 119 episode texts, content identities, vector matrix, query vector, prior report, renderer, packer, and corruption fixtures. |
| PF2 | Execute every name-to-behavior check in Section 6 and bind the behavioral identity to committed traces. A graph walk cannot satisfy this check. |
| PF3 | Prove import and execution order: integrity and leakage, G1, G2, G3, G4, then and only then Q11 query and fact measurement. Plant a G3 failure and prove that fact-key import is unreachable. |
| PF4 | Prove G3 and G4 are mathematically reachable with a committed synthetic orthogonal-pattern fixture; distinguish reachability from success on the 119 real patterns. |
| PF5 | Use content and pattern SHA-256 keys only; reject generated IDs, timestamps, and paths. |
| PF6 | Reproduce E006-P3's 119 eligible identities, vector digest, compact renderer fixtures, and exact packer payloads before new output. Do not rerun or reinterpret its outcome. |
| PF7 | Execute full intended-length recurrence for all cues; record fixed points, runtime-guard exits, repeated states, dominant basins, and energy traces. This PF reports absorbing states rather than assuming they are defects: attractors are the intended absorbing states. |
| PF8 | The exhaustive 119-pattern run detects failures for this fixed store and corruption set, but cannot estimate generalization to new episodes, capacity at other store sizes, biological fidelity, or live answer use. No 35-turn live ablation applies because no inference run is authorized. |
| PF9 | Audit every surrogate. Fixed-point storage can pass without robust basins; one-bit recovery can pass without 10% recovery; bit corruption can pass without natural-language partial-cue recovery; Q11 availability can pass without a correct answer; deterministic Hopfield behavior can pass without hippocampal realism. These residuals are accepted and must appear in the report. |
| PF10 | State that offline recovery and Q11 availability are not answer verdicts. Any usefulness claim requires a separately pre-registered live evaluation with answer scoring and deterministic controls; none is authorized here. |

PF1-PF10 must be committed PASS before any evidence implementation imports the
Q11 fact key. If exploration itself fires G1-G4, the failure artifact replaces
later evidence and records which remaining checks were not reached.

---

## 8. Implementation and evidence order

1. Commit this Rev 4 design with no implementation files.
2. Commit standalone author authorization bound to its commit and SHA-256.
3. Implement the component, reference oracle, fixtures, leakage sentinels, and
   label-blind exploration runner.
4. Commit implementation and tests.
5. Run and commit Preflight Part 1 without importing Q11 labels.
6. If G1-G4 remain reachable, implement, run, and commit PF1-PF10.
7. Lock the exact implementation/module hashes and zero-call settings.
8. Run the binding recovery evidence once.
9. Only if G3 and G4 pass, implement and run the Q11 translation measurement.
10. Commit the Rev 4 report, ledger update, memory update, root digest/status
    updates where required, verification, and PR update.

Git order is evidence. No later result is backfilled into an earlier artifact.

---

## 9. Exclusions

Rev 4 authorizes no embedding or generation calls, live inference, production
change, alternate retrieval arm, parameter sweep, score tuning, new episode
formation, targeted probe reconstruction, sequence memory, multi-attractor
enumeration loop, inhibition-of-return policy, or claim of full hippocampal
replication. Those are distinct mechanisms or evaluations and require their
own prospective designs.

