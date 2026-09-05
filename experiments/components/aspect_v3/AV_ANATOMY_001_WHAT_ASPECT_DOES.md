# What ASPECT-v1 Actually Does

**Status:** `ANALYSIS - measured, not registered; no result moves`
**Date:** September 2, 2026
**Method:** the deployed `episodic._aspect` extractor run on episode text
reconstructed from HH-003's sealed ASPECT contexts. `en_core_web_sm` 3.8.0, the
exact pinned model. Zero model calls, zero embedder calls.
**Population:** four LoCoMo conversations, 1,154 episodes — conv-26 and conv-50
from the DA-touched split, conv-41 and conv-47 from the never-touched split.

---

## 1. The mechanism, in plain terms

ASPECT-v1 is **greedy cost-normalized weighted max-coverage over facets**. Four
moving parts:

**Facets.** Every episode is parsed by spaCy and reduced to a set of strings
drawn from six families: `entity:LABEL:words`, `date:words`, `number:token`,
`event:verb_lemma`, `relation:head:dep:subtree_words`, `noun:chunk_words`. An
episode becomes roughly 31 of these.

**Weight.** Each facet gets an IDF, `log((N+1)/(df+1)) + 1`, computed over the
candidate pool. A facet's *covered value* is the largest `cc80_score × idf` among
episodes already selected.

**Seed.** The protected semantic half is loaded in first, so its facets start
covered at the high CC80 scores of top-ranked episodes.

**Greedy.** Repeatedly admit the episode maximizing

```
marginal_gain / additive_weight(episode)
    where marginal_gain = Σ over the episode's facets of
                          max(0, cc80_score × idf − already_covered)
```

Ties break toward better CC80 rank. Stop when nothing fits or no positive
marginal remains.

The intent is legible and reasonable: after the semantic half has taken the
directly relevant material, spend the other 16k on episodes that introduce
*information the semantic half does not already carry*, preferring cheap
episodes over expensive ones.

That is the design. What follows is what it does.

---

## 2. Measurement 1 — the facet space is 1/3 timestamp

Every LoCoMo turn's text begins with a header of the form
`6:21 pm on 22 July, 2023 | Melanie: `. That header is inside `user_message`, so
it is part of `searchable_text`, so the facet extractor sees it.

Stripping only that header and re-extracting:

| Conversation | Episodes | Distinct facets | **Facet mass from the header** |
|---|---:|---:|---:|
| conv-26 | 208 | 1,901 | **36.9%** |
| conv-41 | 322 | 2,539 | **37.2%** |
| conv-47 | 341 | 2,833 | **41.1%** |
| conv-50 | 283 | 2,389 | **33.6%** |

Between a third and two fifths of everything ASPECT is trying to cover is the
clock, the calendar, and the speaker's name.

The single heaviest facets in conv-26, by total `idf × df` mass, are:

```
mass 208.0  df=208/208  idf=1.00  number:2023
mass 208.0  df=208/208  idf=1.00  entity:PERSON:melanie
mass 205.2  df=176/208  idf=1.17  noun:|_caroline
mass 189.3  df=127/208  idf=1.49  date:2023
mass 189.3  df=127/208  idf=1.49  entity:DATE:2023
mass 169.7  df= 96/208  idf=1.77  noun:melanie
mass 162.3  df= 87/208  idf=1.86  entity:PERSON:caroline
mass 153.9  df= 78/208  idf=1.97  event:make
```

`number:2023` and `entity:PERSON:melanie` are in **every one of 208 episodes**.
`noun:|_caroline` is the pipe delimiter of the header being swallowed into a noun
chunk. Nothing in this list describes what an episode is *about*.

Two things are worth separating here. That the timestamp sits in
`searchable_text` is defensible — it is the same text CC80 embeds, and a memory
system has real reason to make time searchable. That the *facet extractor*
inherits it and spends a third of its coverage objective on it is very unlikely
to have been intended, and no study has ever looked.

---

## 3. Measurement 2 — the IDF weight is degenerate

IDF is supposed to grade facets from common to rare. Measured over the real
candidate pool, it barely grades at all.

| Conversation | Facets appearing in exactly one episode | Median IDF | Max IDF |
|---|---:|---:|---:|
| conv-26 | **70%** | 5.65 | 5.65 |
| conv-41 | **67%** | 6.08 | 6.08 |
| conv-47 | **71%** | 6.14 | 6.14 |
| conv-50 | **67%** | 5.96 | 5.96 |

**The median IDF equals the maximum IDF in all four conversations.** Roughly
seven in ten distinct facets occur exactly once in the whole store, and every one
of them is tied at the ceiling. conv-26's full distribution is
`min 1.00 · p25 5.24 · median 5.65 · p75 5.65 · max 5.65`.

So the weight is not a gradient, it is close to a two-value flag: *seen once*
(ceiling) or *common* (1.0 to 2.4). And since the coverage rule counts only what
the semantic half has not already covered at a higher score, the marginal gain an
aspect candidate can earn is **dominated by its hapax facets** — strings that
appear exactly once in the entire conversation.

A facet occurring exactly once is, nearly by construction, not a shared concept.
It is a particular phrasing, an unusual noun chunk, a parse quirk. The objective
therefore rewards **lexical uniqueness per character** far more than it rewards
conceptual coverage. Those are not the same thing, and the design intent in §1 is
clearly the second one.

There is also a floor effect worth noting: `log((N+1)/(df+1)) + 1` bottoms out at
**1.0**, not 0. A facet present in 100% of episodes is never free.

---

## 4. Measurement 3 — what lands in the channel

Across 120 HH-003 items, comparing question content-words against episode
content-words with the header stripped:

| | Mean share of question terms present per episode | Episodes sharing any question term |
|---|---:|---:|
| Protected semantic channel | 0.224 | 71.1% |
| ASPECT channel | 0.133 | 51.0% |

ASPECT's admissions carry about **60% of the semantic channel's topical overlap**.
Some of that gap is correct and intended — a diversifier seeded on the semantic
half is supposed to go further afield. The question is whether what it finds out
there is useful diversity or lexical noise, and §3 is the reason to suspect the
latter.

A worked example, conv-26, for the question *"What areas is John particularly
interested in for policymaking?"* — ASPECT's first two greedy admissions are a
turn about trying new exercise classes and a turn about camping and mountain
climbing. Neither mentions policy. Both are dense in once-only nouns.

---

## 5. What this is and is not

**Measured, and robust across four conversations including two never touched by
any availability study:** the header share, the hapax fraction, the
median-equals-max IDF collapse, the identity of the heaviest facets, and the
topical-overlap gap.

**Inferred, not proven:** that these degrade selection quality. The chain is
plausible and mechanical — a third of the objective is clock and names, seven in
ten weights are tied at the ceiling, and the marginal gain reduces mostly to
once-only strings — but *plausible mechanism* is exactly the currency the DA arc
traded in, and it is not evidence.

**Unknown:** whether repairing any of this changes what a reader answers. Only a
live run says.

What the measurements do explain, without needing new experiments, is why two
prior results looked strange. TC-011 found ASPECT *worse* than plain CC80 on
availability and registered `NO_CANDIDATE`. HH-003 found it better live by +14 at
`p=.14`. An objective that is one-third timestamp and otherwise dominated by
hapax strings is exactly the kind of thing that would produce a small, unstable,
hard-to-explain effect in either direction.

---

## 6. What this changes about the plan

The five-arm sweep proposed in the thesis draft — ASPECT at shares
`.5/.25/.125`, plus a headroom arm — was drifting toward the pattern the DA arc
died of: a plausible space of variants, explored because it was cheap to explore.
The share arms in particular test *how much* of a mechanism to apply before
anyone has established what the mechanism is doing.

The measurements above suggest a different and much smaller first question, with
a mechanistic reason and a directional prediction attached:

> **Does ASPECT select differently, and answer better, when its facet extractor
> stops spending a third of its objective on timestamps and speaker names?**

That is one hypothesis, one intervention, one prediction, and a defect rather
than an invention. The retrieval path, renderer, budget, share, greedy rule and
CC80 ranking all stay frozen; the only change is what text `prepare_facets` is
given. It is testable offline for *selection change* — does the admitted set
actually move — before spending any reader time at all.

Proposed replacement for the sweep, in order:

1. **Offline, free:** does header-stripping change ASPECT's admitted set at all?
   If the delivered episodes barely move, there is nothing to take to a reader
   and the hypothesis dies for the cost of an afternoon.
2. **Live, if and only if the set moves:** three arms — `CC80` control,
   `ASPECT_v1` incumbent, `ASPECT_clean` — on the development split, confirmed on
   the held-out split.

The share sweep is not cancelled, but it is demoted to *after* somebody
understands the mechanism, which is the order the DA arc got wrong.
