# DMR-004 Report — Deterministic Query-Obligation Compiler

**Status:** `STOP — NO_MECHANICAL_SUFFICIENCY_SIGNAL; CHARACTERIZED`
**Pre-registration SHA-256:** `fd99a9175a5d8048038d5e4d5b70e6a9091c90f71731026dbfdd68dd9eefcfda`, committed at `6ea982fa`
**Amendment:** `amendments/AMENDMENT_001_enumerate_obligation_cardinality.md`
**Compiler:** `src/biological_memory/query_obligations.py`, frozen at `42b45222`
**Grammar `design_sha256`:** `c054b18857f92362bc3947f5d029f502ee6669fa4cfa001eb4579f1ab59f7eae`
**Part 1 record SHA-256:** `d34e50c5ba6bf6127b3a219e7959bdb95be991be223d642e3cc5032fdf4c6e61`
**Corpus digest:** `16e06f6d363ddc9d6743452713fc642b0cedf52c0f86fa62fff8e280f094daa9`
**Date:** August 12, 2026

## 1. Result

On the sealed holdout of 180 adjudicated queries:

| Gate | Statistic | Value | Bar | |
|---|---|---|---|---|
| **G_J** | Youden's J | **0.320** | ≥ 0.50 | **FAIL** |
| **G3** | false-finite rate | **0.188** | ≤ 0.15 | **FAIL** |
| G4 | `LOOKUP` recall | 0.800 | ≥ 0.60 | PASS |
| G5 | well-formed span share | 1.000 | = 1.00 | PASS |
| G6 | internal-only markers | 0 of 48 | = 0 | PASS |
| G1 | purity | zero violations | zero | PASS |
| G2 | determinism | zero differences | zero | PASS |

G_J, G3 and G4 were registered as a joint condition. It fails. The registered
decision is **STOP**.

Sensitivity 0.508, specificity 0.812, balanced accuracy 0.660, raw accuracy
0.706. PF1–PF10 all pass and were committed before the gates ran.

## 2. What the failure is

The compiler is not wrong in a scattered way. Its 31 misses fall into four
families and one of them was predicted, in writing, before the compiler existed.

| Family | n | |
|---|---|---|
| *"Which happened first, A or B?"* | 12 | the hole in the class set, flagged during annotation |
| No interrogative frame — imperative or statement-framed requests | 12 | mostly this program's own probe templates |
| `HISTORY` mapped to `NOVELTY_ONLY` | 3 | self-inflicted by the registration |
| Pied-piping — a preposition before the wh-word | 2 | *"At which university did I present a poster?"* |
| Other superlative | 2 | |

And its 22 false-finites are 20 `LOOKUP`, 1 `CONJUNCT`, 1 `ENUMERATE_N`, in
three families: advice and opinion requests that carry an interrogative frame
(*"Do you have any helpful tips?"*), computed quantities with no registered
marker (*"How old will Rachel be when I get married?"*, *"What percentage of the
countryside property's price…"*), and queries where the two raters disagreed so
the gold took the conservative label.

### 2.1 The largest miss family was predicted and not patched

While producing rater A's development labels, before the compiler existed, this
was recorded with the labels:

> *"Which happened first, A or B" names two referents but makes one request, so
> it is not CONJUNCT under the locked rule and not ENUMERATE_N because no
> integer is stated. It is finite with class OPEN, and the resulting hole in the
> class set is reported rather than patched.*

That family is **31 of 524 queries corpus-wide (5.9%)** and **12 of the 31
holdout misses — the single largest cause.** These queries name exactly two
items. Their evidence obligation is bounded, knowable, and exactly the kind of
signal a stopping controller could use. The registered grammar has no class for
them, and its `first` marker actively demotes them to `OPEN`.

Patching the protocol when this was noticed would have raised sensitivity and
moved the result toward a pass. It was left alone.

### 2.2 The registration penalises its own `HISTORY` class

`completeness_mode` is `NOVELTY_ONLY` for `HISTORY`, and the finite/open
statistic counts only `FINITE`. So a history query the compiler classifies
**correctly** is scored as a miss whenever the gold calls it finite. Three of
the four gold `HISTORY` instances are misses for this reason alone — including
*"What was my previous personal best time for the charity 5K run?"*, which the
compiler gets right.

The reasoning behind `NOVELTY_ONLY` still holds: a value may have had any
number of prior values and the text does not bound them. But pairing it with a
binary FINITE-versus-not statistic makes correct classification cost the same
as failure.

### 2.3 A registered marker fights the grammar

`first` and `last` are registered superlative markers. `last` is far more often
a temporal deictic — *"the music event last Saturday"*, *"which shoes did I
clean last month"* — than a superlative over an unnumbered set. Adding the two
markers during implementation, to match the registration, moved development
Youden's J from **0.363 to 0.220**.

Separating *"last Saturday"* from *"the last one"* needs syntactic analysis §3
of the specification excludes. Within this stage's own constraints, the
registered rule is not implementable in a form that helps.

## 3. What passed, and what that is worth

**G5 at 1.000 and G6 at 0 of 48** are real. Every obligation span is within
bounds, non-overlapping, and exactly the substring it reports, across all 524
queries — including under NFKC and case-folding expansions where index
arithmetic against the original string would silently drift. No registered
marker fires only on this program's own probes.

**G4 at 0.800** is real but narrow, and it moved a lot: 0.536 on development,
0.800 on the holdout. On 35 gold instances, that is a swing worth distrusting.

**G1 and G2** hold under a fresh-interpreter import closure checked against
`sys.stdlib_module_names`, socket and subprocess tripwires, two-process replay
of plan digests, and six perturbation families at zero class changes.

### The structural controls did their job

| Arm | J | false-finite | `LOOKUP` recall | accuracy | passes |
|---|---|---|---|---|---|
| always-`FINITE` | 0.000 | 1.000 | 1.000 | 0.350 | G4 only |
| always-`OPEN` | 0.000 | 0.000 | 0.000 | 0.650 | G3 only |
| **compiler** | 0.320 | 0.188 | 0.800 | 0.706 | G4, G5, G6 |

Answering *"I cannot tell"* to every query scores **0.650 accuracy**. The
compiler scores 0.706. A stage that had registered accuracy as its statistic
would be reporting a 70.6% result off a 5.6-point margin over a control that
does nothing. Youden's J is 0 for both degenerate arms by construction, which is
why it was registered instead — the constraint carried from DMR-001C, where
macro F1 over a dense corpus rewarded frequent firing.

## 4. The annotation held up

| | development | holdout |
|---|---|---|
| `finite` raw agreement | 0.875 | 0.889 |
| `finite` Cohen's κ | 0.752 | 0.770 |
| `plan_class` dispute rate | 0.192 | 0.178 |
| inter-rater Youden's J | 0.759 / 0.770 | — |

Two independent raters reach J ≈ 0.76 with each other. The compiler reaches
0.320 against their adjudicated gold. The gap is not measurement noise.

The gold is conservative by rule — a `finite` disagreement resolves to `false`
— which biases it **against** the compiler's sensitivity and therefore against
a pass. Rater A is not independent of the mechanism; that limitation was
recorded in the protocol before any label existed and applies to every number
here.

## 5. Untested vocabulary

21 of the 48 registered markers fire on neither corpus: `prior`, `formerly`,
`used to`, `originally`, `back then`, `how far`, `altogether`, `mean`,
`median`, `differ`, `more than`, `less than`, `fewer than`, `sum of`,
`enumerate`, `name all`, `name every`, `lowest`, `worst`, `largest`,
`smallest`. No coverage is claimed for them. `SupportMode.NEVER_COMPLETE` is
declared by the schema and emitted by no plan, because an `OPEN` plan carries
no obligation to mark.

## 6. Decision

Per the pre-registration §9 and specification §12:

**The arc has no principled mechanical sufficiency signal.** DMR-001 through
DMR-003 may remain useful fixed-depth retrieval components, but a model-free
adaptive controller is **not authorized**. The failed compiler **must not** be
replaced with a second language-model call inside this arc.

Nothing here authorizes retrieval, an ablation, or a live run. Query
representation alone changes nothing delivered to a reader.

### What this stage cannot claim either way

`CONJUNCT`, `ENUMERATE_N` and `HISTORY` were emitted and not gated, so this
result neither supports nor refutes the specification's claim that those
obligations are representable. The holdout gold holds 10, 2 and 4 instances of
them. Part 1 found the instances do not exist to test it on, and that finding
stands independently of the score.

## 7. What a successor would have to change

Not a threshold. Three structural things, in order of measured cost:

1. **A class for explicitly listed alternatives.** *"Which happened first, A or
   B?"* is 5.9% of queries and the largest miss family. It states its own
   cardinality by enumeration rather than by integer, which the registered
   `ENUMERATE_N` rule cannot see.
2. **A completeness mode that does not punish correct `HISTORY`.** Either
   lineage counts as bounded, or the statistic stops being binary over
   `FINITE`.
3. **Removal of `first` and `last` from the superlative set**, or a way to tell
   a temporal deictic from a superlative that does not need excluded syntax.

None of these is available by retuning. All three change the registered design,
so they belong to a new authorized study, not to this one.

## 8. Artifacts

All under `artifacts/`, all committed before the step that consumed them:

| File | Committed at |
|---|---|
| `query_corpus.json`, `part1_record.json` | `868147ba` |
| `split_manifest.json` | `29319a92` |
| `annotations_dev_rater_a.json` | `29b5cb18` |
| `annotations_dev_rater_b.json`, `gold_development.json` | `510f410d` |
| `annotations_holdout_rater_a.json` | `1b4e1f2f` |
| `annotations_holdout_rater_b.json`, `gold_holdout.json` | `47d47274` |
| `preflight.json` | before the gates |
| `gates_development.json`, `gates_holdout.json` | `75719564` |

PF3 verifies the ordering from git history rather than asserting it: protocol
before any label, labels before the registration, registration before the
compiler, compiler before the holdout labels, holdout labels before the gates —
and the registration commit carrying exactly one file. All five hold. This arc
broke that ordering once before, in DMR-001B, recorded as `DEVIATION_001`.

Test suite: 44 tests in `tests/test_dmr004_query_obligations.py`, all passing.
