# IC-001 - Internal Packing-Priority Counterfactual

**Pre-registration:** `IC_001_internal_packing_counterfactual.md` at
`7b578c54aa5643fbc691ed679aab95e531a9e962`
**Amendment 001:** `no vector recomputation` — **PROPOSED, NOT AUTHORIZED**
**Status:** COMPLETE
**Outcome:** **BRANCH A — PACKING IS A GATE INTERNALLY TOO**

## 1. Result

IC-001 changed one thing in an offline replay of the corrected 121-turn
internal run: packing order. B0 offered the recency window, then the K
threshold hits, then coverage. B1 offered K, then recency, then coverage. The
store, candidate identities, `K = 0.48`, `N = 32`, the selector, the
32,000-character budget, the post-DR-001 renderer, and the measurement code
were held fixed. No inference call, no embedding call, no vector re-derived.

**Q11 availability rose from 6/17 to 7/17: one gain, zero losses.** The gained
item is `civil:Dr. Anara Bekova`. Domain coverage is 3/4 in both arms; art
remains empty in both.

**No targeted probe fell.** Across the eight committed targeted questions,
availability rose from 14/21 to 18/21 with **four gains and zero losses**: Q5
went 0/2 to 2/2 and Q6 went 0/2 to 2/2. Q6 exceeds even the committed T6
value of 1/2.

Under the registered rule this is **Branch A**. Section 5 of the
pre-registration's decomposition consequence follows: part of what PAPER-001
§5 attributes to *selection* is attributable to *packing priority*.

No materiality threshold was registered, matching EC-002's treatment. These
are exact paired counts and support no significance claim; the program holds
no variance estimate anywhere.

## 2. The prior was wrong about the mechanism, right about the size

The pre-registration predicted a smaller effect internally than externally,
because the internal corpus is one continuous conversation where recent turns
and relevant turns overlap far more than in EC-001's discontinuous histories.

The effect is smaller: +1 fact on the breadth probe against EC-002's
109/470 → 261/470. But the **mechanism is identical, and it is not partial**.

| Arm | Probes where K delivered nothing | K episodes delivered | K characters |
|---|---:|---:|---:|
| B0 recency-first | **8 of 8** | **0** | **0** |
| B1 K-first | 3 of 8 | 9 | 14,796 |

Under the deployed order, the similarity path delivered **zero episodes and
zero characters at every one of the eight probes**. Recency consumed the
entire budget every time. This is EC-001's finding — "at least one exchange
clears `K = 0.48` on 232 of 500 questions, yet a non-recency K exchange
survives packing on only 20" — reproduced on the internal corpus at complete
strength. The similarity path was computing candidates and being denied
window space here too.

Recency-first looked defensible for eleven studies. On this corpus it was not
defensible; it was merely *less costly*, because the recency window happened
to carry many of the same facts.

## 3. Per-arm delivery at Q11

| | B0 | B1 |
|---|---:|---:|
| Facts available | 6/17 | **7/17** |
| Domains | 3/4 | 3/4 |
| civil / art / monetary / marine | 4 / 0 / 1 / 1 | **5** / 0 / 1 / 1 |
| Episodes delivered | 8 | **12** |
| Serialized characters | 31,946 | **31,863** |
| Recency episodes / characters | 8 / 31,886 | 10 / 30,653 |
| K episodes / characters | 0 / 0 | 2 / 1,130 |
| Coverage episodes / characters | 0 / 0 | 0 / 0 |
| Candidates skipped, recency / K | 24 / 2 | 22 / 0 |

**B1 delivers four more episodes in 83 fewer characters.** Admitting two small
high-similarity episodes first (turns 2 and 114, 1,130 characters together)
left room for four more recency episodes than the deployed order fitted,
because the deployed walk had already spent the budget on one large episode at
turn 103. This is a priority effect under a binding budget, not a capacity
increase, and it is not a trade.

Delivered source turns:

- **B0:** 119, 68, 73, 83, 89, 96, 103, 4
- **B1:** 119, 68, 73, 83, 89, 96, 4, 12, 112, 1 (recency) + 2, 114 (K)

## 4. Q1–Q8: the LV-001 check, and what it found

Item 6 of the pre-registration is not optional, and its concern was specific:
K-first reorders what recency delivers, and *the opening turns LV-001 found
missing are exactly the material a recency-first order protects*. If K-first
bought breadth by displacing early recency episodes, IC-001 would have
reproduced the LV-001 failure offline and had to say so.

**It did not. The displacement ran the other way.**

| Probe | Turn | Items | Committed T6 | B0 | B1 | Δ |
|---|---:|---:|---:|---:|---:|---:|
| Q1 | 112 | 2 | 2 | 2 | 2 | 0 |
| Q2 | 113 | 2 | 2 | 2 | 2 | 0 |
| Q4 | 115 | 4 | 0 | 3 | 3 | 0 |
| Q5 | 116 | 2 | 2 | **0** | **2** | **+2** |
| Q6 | 117 | 2 | 1 | **0** | **2** | **+2** |
| Q7 | 118 | 5 | 5 | 5 | 5 | 0 |
| Q8 | 119 | 2 | 2 | 0 | 0 | 0 |
| Q10 | 118 | 2 | 2 | 2 | 2 | 0 |

Zero probes fell, on the per-probe grain and in total. The two indicators
agree, so no reading of "Q1–Q8 falls" was required.

At Q11 specifically, B1's window contains the **turn-1 and turn-2 episodes**
that B0 dropped entirely. The turn-1 episode is a K/recency overlap: it clears
`K = 0.48`, the deployed recency walk skipped it on cost, and K-first admits
it. Those are the two formatting-rule plants LV-001 reported the shipped
configuration could not see.

This is an offline availability observation about a different arm, and it is
not a repair of LV-001, which killed the **E005 A3 coverage** configuration on
a live run. It does say that the specific failure mode this section exists to
detect did not occur, and that on this probe the recency-first order was
itself the thing dropping the opening turns.

## 5. Oracle-set overlap

AR-001 carries two easily conflated five-episode sets. Both are reported.

| Arm | Exact 14/17 optimum | Greedy 15/17 |
|---|---:|---:|
| B0 | 0/5 | 0/5 |
| B1 | **1/5** | **1/5** |

The recovered episode is `5c4446e4` at turn 112, common to both sets. B1 gains
it in the **recency** block: K-first freed the space, it did not re-rank
anything.

Reported together with §3's path split, as the surrogate audit requires: a
path can be large and irrelevant, so neither number stands alone. The
combination here is unambiguous — the deployed order spent 31,886 characters
of recency to recover none of the optimum, and K-first recovered one while
spending less.

## 6. Integrity

| Check | Status |
|---|---|
| B0 gate against the committed deployed result | **PASS**, committed at `9d2ecd58` before B1 was opened |
| Fact count, domain count, characters, episode count | 6/17, 3/4, 31,946, 8 — all exact |
| Episode identities and payload SHA-256 | exact |
| Per-domain breakdown | civil 4 / art 0 / monetary 1 / marine 1 — exact |
| Byte-identical to the shipped `pack_stm_payload` | **PASS** |
| B1 precondition: B0 gate committed, git-tracked, passing, reproducing | **PASS** |
| Leakage audit on the mechanism source | **PASS** |
| Deterministic in-process rerun, both arms | **PASS** |
| Source integrity before and after, both phases | **PASS** |
| Model calls / embedding calls / cache misses | **0 / 0 / 0**, enforced |

The B0 gate is the binding one, and it is a stricter faithfulness test than a
count comparison: the fact count could have matched on different episodes, so
identity and payload digest are asserted too.

"Zero model calls" is enforced rather than narrated. `ModelCallGuard` replaces
`llama_cpp.Llama.__init__`, `src.embeddings.provider._get_model`, and
`CarriedEmbedder.__init__` with a raise for the duration of every phase and
records the attempt count. It was armed on all three entry points, and zero
attempts were made.

### Cache binding — an unmet registered clause

Section 3 requires a read-only CC-006 cache with file and canonical content
hashes asserted before and after. **No such cache exists for this corpus and
none can be created without the model calls the same section forbids.** The
only adopted CC-006 cache is EC-002's 96,585-entry LongMemEval cache; the only
internal-corpus vector files are gitignored, unhashed span caches from the
bakeoff.

Amendment 001 proposes a stronger substitute: both arms consume the deployed
run's **committed candidate identities** from `logs/context_match.jsonl`, so no
cosine is recomputed, no ranking re-derived, and no vector read at all. The log
and store hashes are asserted before and after each phase.

**That amendment is PROPOSED and has not been authorized.** Until it is, this
report's arms rest on a substitution the program author has not approved.

## 7. Configuration note: the coverage tier is empty

The pre-registration names three tiers. The deployed configuration populates
two: it is a recency window of 32 plus a `K = 0.48` threshold, with no
coverage selector. Coverage is therefore empty in both arms, and the two
orders differ only in whether K or recency is offered first. The A3 coverage
selector that EC-002's A1 order includes is E005 work and was never deployed
on this corpus.

This does not weaken the comparison — the single variable is still packing
order — but it means IC-001 tests a two-tier instance of the registered
three-tier order.

## 8. Interpretation boundary

**Availability only.** IC-001 shows that packing priority moved availability
on Q11 and on two targeted probes. It does not show that the model would
answer any of them correctly, and §6.4 of the pre-registration forbids a
verdict change without a separately registered live run. LV-001 measured 16/16
offline against 1.5/8 live; that gap is the reason this section exists.

**One probe, one store, one run, no variance.** The program has exactly one
breadth probe, and PAPER-001 §8.2 already concedes a single probe cannot
support a claim about enumeration in general. A +1 on Q11 is one item.

**The path result is the durable finding, not the +1.** That the K path
delivered nothing at 8 of 8 probes under the deployed order is a fact about
the deployed pipeline, not about this probe's answer key. It is the internal
counterpart to EC-002's external result and it does not depend on the breadth
count moving at all.

## 9. What this does and does not authorize

Branch A makes §6's recalibration conditions **live, not satisfied**. All five
must hold before any second internal replay is scoped, and three are outside
this report:

1. Branch A with Q1–Q8 not falling — **met**.
2. Candidates drawn only from §5's availability-mediated set — Studies 003–007's
   LTM read path, Study 009's 9.0-vs-12.0 contrast, Study 010's breadth-only
   finding, E005's selector arms. **Nothing else.**
3. Each candidate a separate registered replay, one at a time — **not a survey**.
4. Availability is not a verdict; any verdict change needs a live run,
   separately registered.
5. **Muzaffer authorizes explicitly, with the compute cost stated.**

Said plainly, as §6 requires: re-running seven studies live is a different
order of budget than one offline replay, and it arrives after a decision to
move toward a product. This replay cost zero model calls. That is not the
comparison.

The graveyard stays closed. Dreaming and distillation, promotion filters,
density and IDF, the topic layer, query routing, graph edges, and ANN all
failed *upstream* of delivery. A mechanism that never formed the right record
cannot be helped by delivering records differently.

## 10. Artifacts

| Artifact | SHA-256 |
|---|---|
| `runs/ic001/b0_recency_first/b0_gate.json` | `717e08c2dada9fe6ab00e37d8001b83376acf349ec637c163c7dd453775daf89` |
| `runs/ic001/b0_recency_first/b0_arm.json` | `aa6bb541fd3bde79f2b3691177cd177ae2213d84f71826039cd31874ea59b578` |
| `runs/ic001/b1_k_first/b1_arm.json` | `439f428693010316e9f09b602ec155ad894393e0271404b52c5acc04b27c7bcf` |
| `runs/ic001/b1_k_first/paired_comparison.json` | `5dad3eabfac3df391669178f20176053fd6677ebc6bd0ac54a05bdcbbbeb5271` |
| `runs/ic001/b1_k_first/verdict.json` | `04bf0d8603a7a07bdd9513f18ad2ca90ac47db272a3ddd734cce3eda8c769e23` |

Decision rule committed at `7b578c54` before any arm ran. B0 evidence
committed at `9d2ecd58`. B1 evidence committed at `4947582e`, before this
interpretation.

## 11. Closeout

- [x] Decision rule committed before B1 output was opened — `7b578c54`
- [x] B0 gate: committed deployed result reproduced, episode identities asserted
- [x] Zero new model calls, zero misses — enforced, not narrated
- [ ] Cache hashes asserted before and after — **unmet; Amendment 001 pending**
- [x] Per-arm Q11 facts and per-domain counts
- [x] Character and episode split by path, both arms
- [x] Oracle-set overlap, both arms, both AR-001 sets
- [x] Q1–Q8 per-probe, both arms
- [x] Paired gains and losses
- [x] Branch verdict
- [x] `PAPER_001.md` §5 updated
- [x] Ledger entry; `README.md` and `AGENTS.md` digest in the same PR
- [x] `ERRATA.md` — **not triggered.** No committed number moved. B0
      reproduces 6/17 at 31,946 characters exactly; what changes is the
      attribution of part of that figure, which is a PAPER-001 §5 revision
      and not a correction
