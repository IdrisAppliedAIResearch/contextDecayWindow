# TC-008 Report — relevance-gated source-session spread

**Standing:** `REGISTERED-OFFLINE`
**Status:** `COMPLETE`
**Pre-registration:** `TC_008_PRE_REGISTRATION.md`
**Pre-registration commit:** `a78bbae30455b1d299547dd96d414c03b9098f53`
**Pre-registration SHA-256:** `b40714d4557f7b8510970542856154d920e9f5e1a0f88a4b578c0ee4a9203fbd`
**Final G0 commit:** `18077ef7c0a124bcfc83cfef7deffa045971c63d`
**Question-level artifact commit:** `856e642fe7712f622053062bddeabb35fe3d72da`
**Registered disposition commit:** `b43c1d859c470e630b6ff73527d0090460dc562c`
**Descriptive attribution commit:** `0f132a582ab341f878b426fac5cbf4d419e255b7`
**Date:** 2026-08-23

## Verdict

Replacing TC-007's embedding-cluster novelty with source-session novelty does
not preserve semantic retrieval or improve breadth. It increases represented
sessions, but at 16k it loses required evidence on both direct and breadth
questions. At 32k complete delivery ties dense, while breadth identity delivery
is one fact worse.

> **Disposition: `DENSE_CARRIES_SIGNAL`; no session split is selected.**

In plain terms: the selector successfully spreads across conversation sessions,
but it spreads to the wrong sessions. A session being new is not evidence that
it contains something needed for the question.

## Registered result

The primary endpoint is paired required-identity delivery on 44 breadth
questions. The joint guardrails are breadth, combined and targeted complete
evidence. Works alpha is `.01/6`; signal alpha is `.10/6`.

| Budget | Endpoint | Dense | Session | Gains | Losses | Net | Session p | Dense p | Reading |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 16k | Breadth identities | 129 | 125 | 1 question / 1 id | 4 questions / 5 ids | -3 questions / -4 ids | .9688 | .1875 | Adverse; no breadth signal |
| 16k | Breadth complete | 16 | 13 | 0 | 3 | -3 | 1.000 | .125 | Fails noninferiority |
| 16k | Combined complete | 749 | 728 | 2 | 23 | -21 | 1.000 | 9.72e-6 | Dense guardrail fires |
| 16k | Targeted complete | 643 | 629 | 2 | 16 | -14 | .9999 | .000656 | Dense guardrail fires |
| 32k | Breadth identities | 157 | 156 | 0 questions / 0 ids | 1 question / 1 id | -1 / -1 | 1.000 | .500 | One adverse question |
| 32k | Breadth complete | 27 | 27 | 0 | 0 | 0 | 1.000 | 1.000 | Exact tie |
| 32k | Combined complete | 810 | 810 | 0 | 0 | 0 | 1.000 | 1.000 | Exact tie |
| 32k | Targeted complete | 680 | 680 | 0 | 0 | 0 | 1.000 | 1.000 | Exact tie |

The session arm cannot be `SESSION_SPREAD_WORKS` because it improves breadth at
neither budget, fails breadth-complete noninferiority at 16k, and fires both
16k dense guardrails. Dense does not clear a two-budget works rule because 32k
is a complete-evidence tie, so the registered lower disposition is
`DENSE_CARRIES_SIGNAL`.

## Comparison with TC-007 A3

Source sessions do not repair A3; they make its 16k semantic cost larger.

| Budget | Read | Dense | A3 | Session |
|---:|---|---:|---:|---:|
| 16k | Combined complete | 749 | 739 | 728 |
| 16k | Targeted complete | 643 | 637 | 629 |
| 16k | Breadth complete | 16 | 13 | 13 |
| 16k | Breadth identities | 129 | 126 | 125 |
| 32k | Combined complete | 810 | 812 | 810 |
| 32k | Targeted complete | 680 | 681 | 680 |
| 32k | Breadth complete | 27 | 27 | 27 |
| 32k | Breadth identities | 157 | 158 | 156 |

At 16k, 27 questions change required-identity delivery. Three are unique
session-spread gains. Nine losses are shared with the fixed 50/50 protection
used by both split arms. Fifteen additional losses are attributable to source-
session grouping because A3 preserves evidence the session arm drops.

The 16 targeted evidence carriers lost at 16k have dense ranks 27–52, median
41. They are not obscure store tails. The dense half stops before them, and the
session route fails to rescue them; A3 rescues eight.

## What happened on actual breadth questions

The one 16k breadth-share gain is “How old is Jolene?” Session spread adds a
required candidate at dense rank 87, moving 2/required to 3/required, but the
answer remains incomplete.

Four breadth questions lose required identities at 16k:

- “What shelters does Maria volunteer at?” falls 3 to 2 and loses completeness.
- “What causes has John done events for?” falls 4 to 2 and loses completeness.
- “What helped Deborah find peace when grieving deaths of her loved ones?”
  falls 4 to 3 and loses completeness.
- “What gifts has Deborah received?” falls 2 to 1 while remaining incomplete.

For the first two, represented-session counts rise from 23 to 31/32 while
required evidence falls. For the third they rise from 22 to 30. This directly
rejects represented-session count as a useful spread endpoint.

At 32k only “What recipes has Joanna made?” changes: required delivery falls
from 7 to 6 while both arms remain incomplete.

## Mechanism reading

Preflight already showed the treatment adding lower-ranked candidates and
displacing stronger semantic candidates. The outcome identifies which side of
that trade carries evidence. Source-session novelty is too coarse: every query
is encouraged toward previously unseen sessions even when its answer is direct,
and on breadth questions it covers sessions without knowing which session holds
the missing required item.

This does not show that protected spread is impossible. It closes this specific
proposal: a fixed 50/50 share plus a once-per-source-session `0.1` bonus. A
successor would need a mechanism that predicts missing answer evidence better
than global session novelty; simply touching more sessions is ruled out as the
certifying property.

## Integrity

G0 passed before outcomes with 2,214 tests, 3,484 exact TC-007 payload checks,
1,742 treatment payload checks, 70,736 mechanism-step checks and two identical
fresh-process prefixes. The committed label-blind manifest contains 871
questions and no answer/evidence keys.

The accepted run used two fresh complete workers. Both produced:

- frozen selections SHA-256:
  `0ef905c5fa12e3f6d487fdaab5d03cbba60276928369e11d12986119dee0e78b`;
- per-question SHA-256:
  `55fd2b965a075d100ea1ed742e30db2391196fe6f12f46772fdbd183455a065e`;
- diagnostics SHA-256:
  `f97f90707381d9219810de5b5eca64b0f1453b53f9b4e0a4d170aa19f17fd284`.

There were 2,236 cache hits per selection/measurement phase, zero cache misses,
zero embedding calls and zero LLM/generative calls. Under programme terminology
the run is model-free because that term counts LLM calls; embeddings are
reported separately. The final closeout suite passes 2,215 tests.

## Claim boundary and handoff

TC-008 measures exact evidence availability on used LoCoMo development data.
It does not measure whether a reader could answer from partial evidence, choose
an enterprise budget, optimize the spread share, or authorize deployment.

The offline fallback remains full-budget dense retrieval. The next decision is
reader behavior, as the user requested. That work must be separately
preflighted and pre-registered before any answer generation; TC-008 does not
silently start it or choose its reader arm.
