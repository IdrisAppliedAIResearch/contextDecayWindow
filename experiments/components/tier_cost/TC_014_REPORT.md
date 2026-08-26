# TC-014 one-hop traversal component ablation — report

**Status:** `CHARACTERIZED`; two budget-specific component signals  
**Part 1 commit:** `724cfde6`  
**Design commit:** `cb3cec9a`  
**Registration SHA-256:** `8ea94784042fd6fd6be14febc65e042079c98f49502b55a00930f98112b06375`  
**Preflight commit:** `a66ba248`  
**Outcome commit:** `ca66d772`  
**Date:** 2026-08-25

## Result

Two isolated controls help at one budget each. Explicit parent binding, global
assignment and their requested combination with utility packing do not.

| Arm | 16k combined / targeted / breadth | 32k combined / targeted / breadth | Registered disposition |
|---|---:|---:|---|
| Full CC80 | 771 / 666 / 17 | 819 / 689 / 24 | control |
| TC-013 fan-out | 763 / 654 / 16 | 821 / 689 / 26 | control |
| Parent binding | 763 / 655 / 17 | 816 / 685 / 25 | `NO_HELP` |
| Global assignment | 754 / 651 / 15 | 819 / 686 / **27** | `NO_HELP` |
| Utility-first packing | 761 / 653 / 16 | **822** / **689** / **27** | `BUDGET_SPECIFIC_HELP` |
| Opportunity admission | **770** / **661** / **19** | **826** / **692** / 25 | `BUDGET_SPECIFIC_HELP` |
| T2+T3+T4 combined | 765 / 658 / 15 | 815 / 685 / 24 | `NO_HELP` |

## Which components helped

### Exact opportunity admission helped at 16k

Against TC-013 at 16k, the opportunity guard has 16 complete gains and 9
losses overall, 11/4 targeted and 3/0 breadth. Combined, targeted and breadth
nets are `+7/+7/+3`; breadth required identities are `+3/-2`, net `+1`.
Conversation nets are `+4/-2/+4/+1`. This clears the registered `HELPS` cell.

The guard keeps a median 17 of 25 proposed children at 16k and 36 of 52 at
32k. It rejects median 8/16 only when the child's raw ASPECT value does not
cover the exact CC80 identities lost in a real counterfactual insertion. Every
retained child fits; no threshold or coefficient was tuned.

At 32k it still improves combined completion by 5 and targeted by 3 versus
TC-013, but breadth is `1 gain/2 losses` and breadth identities are `3/6`.
That is `HURTS` under the locked joint rule, not a second pass. Descriptively,
its 826/692/25 totals exceed full CC80's 819/689/24, but TC-014 did not register
the paired opportunity-versus-full-CC80 contrast. No inference is attached to
that post-result comparison.

### Utility-first packing helped at 32k

Utility packing changes no edge ownership. At 32k it has one combined gain,
zero losses, one breadth gain, zero breadth-identity losses, and no targeted
change versus TC-013. All of the gain is in `conv-48`; the other conversations
tie. This clears `HELPS` narrowly and raises totals to 822 combined and 27
breadth while retaining 689 targeted.

At 16k it has one gain and three losses overall, including a targeted net of
`-1`, so the effect is budget-specific.

## Which components did not help

Parent binding raises median chosen parent-child cosine from about `.56-.58`
to `.68-.69`, yet at 32k it loses five combined, four targeted and one breadth
completion versus TC-013. At 16k combined is unchanged. More coherent edges
are not more answer-bearing edges.

Global maximum-weight assignment loses 9 combined at 16k and 2 at 32k. It
raises 32k breadth from 26 to 27 but loses three targeted completions. Maximizing
summed edge utility reallocates ownership in ways that harm individual
questions.

The requested T2+T3+T4 combination is not additive. It gains two combined and
four targeted completions at 16k but loses one breadth completion; at 32k it
loses six combined, four targeted and two breadth. Its registered disposition
is `NO_HELP` at both budgets.

## Interpretation

The traversal signal is not “bind and optimize the graph harder.” The useful
controls operate at admission time:

1. preserve TC-013's independent one-hop roots;
2. compare a child with the semantic evidence it actually displaces; and
3. when capacity binds less severely, prioritize already-chosen edges by their
   utility rather than parent order.

The results also show that the two useful controls solve different budget
regimes. They were not combined in this registration, and doing so after seeing
the outcome would be tuning. No combined opportunity-plus-utility arm is
authorized here.

## Integrity and boundary

Preflight reproduced 1,742 TC-013 edge/allocation traces and 1,742 full-CC80
payloads, matched every Part 1 distribution, verified matching against a small
exhaustive optimum, and checked 8,710 unique arm allocations. It used 2,236
cache hits, zero misses, zero embedding calls and zero LLM/generative calls.
Thirteen focused TC-010 through TC-014 tests pass.

The first preflight execution completed and froze all 871 rows, then failed
while serializing a NumPy boolean in the report. The reporting value was cast
to a native boolean; the complete frozen selection file was summarized and
verified without rerunning or changing selection. Labels remained sealed until
the finalized Preflight passed.

This remains LoCoMo development evidence availability. It does not establish
reader use, transfer, a production default, an optimal objective, or an optimal
budget share. No answer run or deployment change is authorized.

