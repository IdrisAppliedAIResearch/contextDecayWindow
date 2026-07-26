# Decision Record — Information-Expressed, Diversity-Floored Retrieval Budget

**Study:** 007
**Tasks:** S7-T-002 (decision record), S7-T-004 (stage-interface contract check)
**Pre-registration:** `experiments/study_007/pre_registration.md`
**Binding amendment:** `experiments/study_007/amendments/AMENDMENT_001_delivered_information.md`

---

## 1. The finding this responds to

Study 006 fixed formation and lost breadth. All four domains formed for the
first time in the program — 200 records, 100% offset-verbatim, zero non-content,
zero inference calls, compression improved to 6.55% — and both breadth probes
then scored 0.0, against a control whose store was demonstrably poorer.

Study 006's own diagnosis was that retrieval returns a fixed **count** of
records while span selection made each record ~17× smaller, so delivered
information collapsed. **Measurement refutes the magnitude of that diagnosis**
(Amendment 001). Delivered LTM text fell from 21,805 to 13,130 characters at
Q11 — a factor of 1.66, not the ~35 the pre-registration projected — because
the read path renders a distilled record's whole source episode rather than its
selected span.

What did separate the arms is **topic coverage inside the block**:

| Arm | Q11 LTM episodes | Distinct topics | Q11 score |
|---|---:|---:|---:|
| Study 006 treatment | 4 | **2** | 0.0 |
| Same-seed control | 5 | **4** | 0.0 |

Neither arm scored, but only the control had four-domain material in front of
the model. The treatment could not have enumerated four domains from what it
received; the control could have and did not. Those are different failures and
only the first is a retrieval problem.

**Why the treatment's coverage narrowed.** Ranking is by span. 200 spans, 50 per
topic, resolve to 69 distinct source episodes. The top 5 spans by similarity to
a breadth query cluster in whichever topic the query's wording most resembles,
and they then collapse by source episode, so the block ends up holding 4
elements drawn from 2 topics. Under whole-turn selection each record *was* an
episode and the top 5 spread naturally across topics.

Coarse granularity had been supplying per-domain diversity **accidentally**.
Study 006 removed the accident without replacing it with anything.

## 2. Decision

Two changes to LTM retrieval, and nothing else.

### 2.1 Budget expressed in information, not record count

The LTM block is filled to a character budget `B_ltm` rather than a top-M count.

**Charged at rendered cost** (Amendment 001 §4.1): a record costs the characters
it contributes to the rendered `<retrieved_ltm>` block — its resolved source
episode's `user_message` + `assistant_message` — after identifier dedup. A
record whose source episode is already admitted costs zero and consumes no slot.

Charging at stored span size was the pre-registration's assumption and is
rejected: it would make the budget as decorative as the count it replaces, since
the quantity constrained would not be the quantity delivered. That is the same
class of error one interface further down.

### 2.2 Per-domain diversity floor, then similarity fill

**Phase 1 (floor):** each canonical topic present in distilled LTM gets its top
`k_min` spans by cosine similarity to the query. Sparse topics contribute what
they have; the shortfall is not redistributed. Under budget pressure floor
selections are admitted round-robin across topics, highest similarity first
within each, so no topic is starved by another's longer episodes.

**Phase 2 (fill):** remaining budget goes to all not-yet-selected spans by pure
global cosine similarity — topic-agnostic, no per-topic cap.

The floor makes coverage structural. The fill preserves targeted relevance. This
is the explicit version of what whole-turn granularity did by accident.

### 2.3 Supporting changes

- **Containment dedup.** An LTM entry whose source episode is already in the STM
  block is dropped and logged; the freed budget is refilled under the same phase
  rules, so a dropped floor selection is replaced from its own topic. Measured,
  a containment hit is exact duplication of a multi-thousand-character episode,
  not the partial redundancy the pre-registration assumed.
- **Floor protection.** No ranking path may evict a floor selection.
- **Named departure from Study 004.** Tier-neutral count-ranking of a merged
  pool is replaced by tier-budgeted assembly. This is part of the component
  under test, not an incidental edit.

## 3. Rejected alternatives

| Alternative | Rejected because |
|---|---|
| **Raise top-M alone** (5 → 15) | Treats the symptom. More slots still fill by global similarity, so a query that clusters in one topic buys more of that topic. It also cannot bound delivered size, since element cost varies ~27× between a short and a long episode. |
| **MMR with tunable λ** | Diversity becomes a continuous knob with no pre-registered value, tuned on the same replay data used to validate it. A hard per-topic floor is falsifiable — the log either shows four topics or it does not — and λ is not. |
| **Per-domain quota with no similarity fill** | Guarantees breadth by construction and destroys targeted recall, inverting Study 006's failure instead of fixing it. The floor is deliberately a minority of the budget for this reason. |
| **Render span text instead of the source episode** | The single most defensible repair, and still rejected for this study: it is a second concurrent change to the mechanism under test, it would land only in the treatment and silently rewrite the control, and it would make this study incomparable to the Study 006 result it exists to improve on. Full reasoning in Amendment 001 §6. **Leading candidate for Study 008.** |
| **Fix formation instead** (per-domain selection guarantees) | Formation already passes 4/4. The store contains all four domains' facts; the failure is downstream of it. Pre-registered as the escalation path only if the replay gate cannot deliver coverage from this store. |

## 4. Stage-interface contract check (S7-T-004, Correction 4)

The standing rule adopted in this pre-registration:

> If any study changes the granularity, units, or size distribution of what a
> stage emits, every downstream stage's budget, cap, or threshold that consumes
> that output must be explicitly re-derived, and the re-derivation recorded in
> the pre-registration — even if the downstream stage is otherwise out of scope.

Study 007 changes the units of LTM retrieval output from *a count of records* to
*a character budget over rendered episodes*. Every downstream consumer of
retrieval output is enumerated below and re-derived.

| # | Consumer | Location | Assumed under Study 006 | Re-derived for Study 007 |
|---|---|---|---|---|
| 1 | Arbitration final cap | `arbitration.py:51` — `registered_cap = k_stm + ltm_top_m` | LTM contributes exactly `ltm_top_m` slots | LTM contributes a variable number of elements bounded by `B_ltm`. The cap becomes `k_stm + len(ltm_selected)`, so STM's allowance is unchanged and LTM's is set by the budget. **Changed.** |
| 2 | Tier-neutral ranking | `arbitration.py:50` | Both tiers emit comparable units, so one similarity sort is fair | False since Study 006: STM emits episodes, LTM emits spans resolving to episodes. Replaced by tier-budgeted assembly with floor protection. **Changed — the named departure.** |
| 3 | LTM candidate truncation | `retrieval_engine.py:279` — `candidates[:self.LTM_TOP_M]` | Top-M by similarity is the selection | Truncation moves into the floor/fill policy. The scorer must return **all** scored candidates so the floor can reach a low-similarity topic. **Changed — a silent top-5 truncation here would make the floor unimplementable.** |
| 4 | Identifier dedup | `arbitration.py:28-39` | One record ↔ one episode | Many records → one episode (200 → 69). Dedup must run **before** budget accounting or the budget over-counts. **Ordering constrained.** |
| 5 | Containment against STM | *did not exist* | — | New. Runs after identifier dedup, before refill. |
| 6 | Tagged renderer | `context_builder.py:131` | Renders `user_message`/`assistant_message` per element | Unchanged in behaviour, but it is the **definition of rendered cost** and therefore the authority the budget is charged against. Budget accounting calls the same renderer rather than re-deriving lengths, so the two cannot drift. **Contract made explicit.** |
| 7 | Context-ceiling monitor | `estimate_tokens` (chars ÷ 4) | Grows with record count | Now bounded by construction: `B_ltm` caps the LTM block directly. The monitor stays, and the replay gate additionally projects peak context < 60% of `--ctx-size` before the run. **Re-derived.** |
| 8 | `ltm_context_episodes.csv` | `file_writer.py:67` | One row per LTM element, count-oriented | Retained unchanged for cross-study comparability; `retrieval_budget.csv` is added alongside carrying chars, phase, and per-domain split. **Additive.** |
| 9 | Arbitration events log | `file_writer.py:51` | `final_set_size`, `ltm_episodes_in_final_set` | Both remain meaningful; character fields live in the new log. **Unchanged.** |
| 10 | STM retrieval (N + K) | `retrieval_engine.py:331-353` | — | Out of scope, untouched, diff-reviewed. Consumes no retrieval-side budget. **Unchanged, verified.** |

**Result:** no downstream consumer still assumes a record count. Items 1, 2, 3
change; item 4 gains an ordering constraint; item 5 is new; items 6 and 7 are
re-derived without behavioural change; 8–10 are unaffected.

**Item 3 is the one that would have silently broken the study.** `_score_ltm_rows`
truncates to `LTM_TOP_M` before returning. A floor implemented downstream of
that truncation would only ever see the global top 5 and could never reach a
topic that ranks below them — the floor would appear implemented, log its
phases, and guarantee nothing. This is a third instance of the same failure
class, found by the same check, before it was written.

## 5. Locked parameters

| Parameter | Value | Status |
|---|---|---|
| `B_ltm` | **32,000 chars** | **LOCKED** at S7-T-017; smallest sufficient over a 16,000–64,000 sweep |
| `k_min` | **1 per topic** | **LOCKED** at S7-T-017; reduced only after raising `B_ltm` to 140,000 failed the targeted fixture at `k_min = 2` |
| Fill rule | pure global similarity, no topic cap | locked |
| Floor protection | floor selections not evictable | locked |
| Containment dedup | drop LTM entry, keep STM episode | locked |
| Budget charged at | rendered cost, after identifier dedup | Amendment 001 §4.1 |
| STM (N + K) | unchanged | carried |

Final calibrated values are recorded in `replay/replay_report.md` and in §5 of
the pre-registration before the ablation runs. No post-run changes.

**Recorded before the run (Amendment 002 §6):** at the locked parameters the
diversity floor is *not* what produces four-domain coverage at the probes — the
budget alone produces it, and `k_min = 0` reaches 4/4 at `B_ltm = 32,000`. The
floor is causal only at 24,000–28,000 with `k_min = 2`, where the targeted
fixture fails at an own-domain share of 0.215. A Bar 1 pass is therefore
attributable to the component and specifically to the information-expressed
budget, and the report may not credit the floor with it. The floor's exam is
Bar 2.

## 6. Correction 1 — UTF-8 in code (S7-T-003)

`src/study/script_loader.py` opened the script with the platform default
encoding, the only such open in `src/`. Study 006 worked around it with
`PYTHONUTF8=1`. A study whose validity depends on an environment variable, with
silent corruption as the failure mode, is fragile.

**Implemented:**
- `open(path, "r", encoding="utf-8")`, explicit.
- `script_digest()` — SHA-256 of the decoded text normalized to LF. LF
  normalization is required because `core.autocrlf=true` rewrites the working
  tree without changing the committed blob; every CR in this script is
  pretty-print whitespace between JSON tokens, none inside a string value.
- `load_script(..., expected_digest=...)` aborts before returning on mismatch,
  and `StudyRunner` passes the pre-registered digest, so the abort happens
  before any inference is spent.

**Verified** (`tests/test_script_loader_encoding.py`): the committed script
still digests to the value Studies 005 and 006 recorded
(`d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01`); the digest
is insensitive to line endings but sensitive to content; loading in a subprocess
with `-X utf8=0` and a cp1252 locale — the exact configuration that produced
Study 006's quarantined mojibake run — yields the correct digest; a tampered
script aborts with the expected message.

**The test is not vacuous.** Reading the same file under `-X utf8=0` without an
explicit encoding digests to `5eb93a82fcbd3abb78f46ab01b5a150256ca3e9291668d91cc208fae35dfaabe`,
which the assertion rejects. The pre-fix code path would have been caught.

`PYTHONUTF8=1` remains set for consistency with Study 006's recorded runtime,
but correctness no longer depends on it.

## 7. Authorization

Authorized by the study author (Muzaffer Ozen, Idris Applied AI Research) under
the standing instruction that Study 007 proceeds end to end, registering
amendments as formal artifacts where the pre-registration meets evidence that
contradicts it rather than halting.

Two such registrations are already on the record before implementation began:
Amendment 001 (the delivered-information premise), and item 3 of the
stage-interface table above (the truncation that would have made the floor
inoperative). Both were found by applying the pre-registration's own Correction
4, and both were found at zero run cost.
