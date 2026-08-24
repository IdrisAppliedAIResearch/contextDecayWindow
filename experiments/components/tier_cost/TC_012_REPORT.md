# TC-012 dynamic ASPECT matrix probe — report

**Status:** `NO_DYNAMIC_PROMPT_SIGNAL`; `RESIDUAL_BINDER_LIMITED`  
**Design commit:** `76fef928`  
**Registration SHA-256:** `2310e768a232a52c63cfaba655b4ed625702cd64f6615e6adb98ac557f870359`  
**Preflight commit:** `6304e69d`  
**Outcome commit:** `abf0c02b`  
**Date:** 2026-08-24

## Result

Recomputing ASPECT's semantic relevance against the growing selected context
after every hop is actively harmful. It moves the cue away from the question,
reaches deeper-ranked candidates, and loses both direct and breadth evidence.

| Budget | Arm | Combined | Targeted | Breadth |
|---:|---|---:|---:|---:|
| 16k | Full CC80 | **771** | **666** | **17** |
| 16k | Static ASPECT | 749 | 645 | 15 |
| 16k | Dynamic prompt | 720 | 635 | 8 |
| 16k | Residual aspect | 753 | 649 | 15 |
| 32k | Full CC80 | **819** | **689** | **24** |
| 32k | Static ASPECT | 810 | 680 | 23 |
| 32k | Dynamic prompt | 787 | 671 | 20 |
| 32k | Residual aspect | 810 | 681 | 23 |

Against static ASPECT, dynamic prompt has combined gains/losses 2/31 at 16k
and 3/26 at 32k. Breadth is 0/7 and 0/3; all four conversation nets are
negative at both budgets. It clears neither registered bar.

Against full CC80, dynamic prompt is -51/-32 combined and -9/-4 breadth.
There is no trade in which the dynamic losses buy breadth.

## Mechanism reading

The dynamic-prompt cue remains anchored, but its median cosine to the original
question is only `.744` at 16k and `.729` at 32k. Its median spread candidate
comes from CC80 rank 128/170, versus static ASPECT's 77/126. Repeatedly adding
selected content creates semantic feedback: the selector increasingly asks for
more of what it has already followed. ASPECT's facet objective does not correct
that drift; it makes the newly steered relevance scores govern coverage too.

Residual ASPECT is numerically less harmful and descriptively improves static
ASPECT by 4 gains/0 losses at 16k; at 32k it has 1/1 combined, with no breadth
changes at either budget. This is not a registered signal. Part 1 showed the
exact lexical residual binder changes only 146/871 selected sets at 16k and
71/871 at 32k, with median cue/query cosine 1.0 because nearly every hop falls
back to the original query. The result characterizes a mostly inert binder, not
the broader thesis of question-obligation-aware retrieval.

## Integrity and boundary

Preflight reproduced 3,484 full-CC80/static-ASPECT identities and payload
digests, checked 117,966 dynamic updates, reproduced all Part 1 activity counts,
and froze selection SHA-256
`0409bb83f82413b4d28f369ed6507d3f2165f6ac22593a1c2a217b6b8a77d7c0`
before labels opened. It used 2,236 cache hits with zero misses and made zero new
embedding or LLM/generative calls. Outcome measurement also made zero calls.

This closes the exact `.3/.7` growing-context cue inside fixed 50/50 ASPECT on
these used conversations. It does not close all dynamic relevance, alternative
query-obligation binders, or smaller adaptive shares. Full CC80 remains the
fallback. No tuning, answer run, deployment or adoption is authorized.

The final repository suite is 2,253 passed.
