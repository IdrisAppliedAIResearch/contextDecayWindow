# Study 007 — LTM Analysis (S7-T-026)

**Observational only. No pass/fail interpretation; the bars are scored in
`experiments/study_007/evaluation/`.**

## Formation invariance (Bar 3's evidence, restated as measurement)

| Measure | Study 007 treatment | Same-seed control | Study 006 treatment |
|---|---:|---:|---:|
| Distilled content records | 200 | 200 | 200 |
| Distilled characters | 28,498 | 29,214 | 29,214 |
| Non-content records | 0 | 0 | 0 |
| Unfaithful at recorded offsets | 0 | 0 | 0 |
| Inference calls in dreaming | 0 | 0 | 0 |
| Dream events | 31/61/91/111 | 31/61/91/111 | 31/61/91/111 |

The control reproduces Study 006's treatment to the character. The Study 007
treatment differs by 716 characters, and that difference is expected rather than
a formation regression: the arms diverge from turn 32, so the raw store the
dream engine reads is not the same text. The **policy** is unmodified — same
segmenter, same salience, C = 50, same floor, same dedup — and it still produces
200 records, 4/4 domains, zero junk, zero inference calls.

## Delivered LTM information — the quantity Study 007 set out to change

| | Study 006 treatment | Study 007 control | Study 007 treatment |
|---|---:|---:|---:|
| LTM block at Q11 (chars) | 13,130 | **13,130** | **33,406** |
| LTM block at Q14 (chars) | 16,027 | **16,027** | **34,051** |
| Episodes in block at Q11 | 4 | 4 | 7 |
| Distinct domains at Q11 | 2 | 1 | **4** |

The control's probe blocks match Study 006's exactly, which is the replication
check that makes the treatment comparison meaningful.

Across the run: 90 turns carried a non-empty LTM block, mean 31,016 characters
delivered, **mean budget utilization 96.9%**, and the 32,000-character budget was
never exceeded on any of 121 turns. Mean 7.7 records per turn, of which 2.1 were
floor selections and 5.5 fill.

## Containment dedup

455 drops across 90 turns, **mean 5.1 per turn**. Every drop is an episode
already present verbatim in the STM block, so the rule reclaimed roughly a fifth
of the budget per turn from exact duplication. Amendment 001 predicted this would
be larger than the pre-registration assumed, because the read path renders whole
source episodes rather than spans; it was.

Record-to-episode collapse averaged 60.3 records per turn — the 200-record store
resolving toward its 69 distinct source episodes, exactly the effect that made
charging the budget at span size untenable.

## Floor versus fill, and the topic-count constraint

Only **10 of 90** LTM turns had all four canonical topics present, because topics
accumulate as dream events fire at 31/61/91/111. For most of the run the floor
had one, two, or three topics to serve, so `k_min = 1` reserved correspondingly
little. At the probes, where all four topics exist, the floor placed 4 records
and fill placed 3–4.

Per-topic character split at the probes:

| Turn | Split across four topics (chars) | Total | Utilization |
|---:|---|---:|---:|
| 120 | 16,979 / 5,983 / 4,629 / 3,927 | 31,518 | 98.5% |
| 121 | 10,539 / 7,886 / 7,480 / 5,983 | 31,888 | 99.7% |

At Q11 the dominant topic still takes 54% of the budget — fill following
similarity, as designed — while the floor guarantees the other three are present
at all. That is the mechanism doing exactly what it was built to do.

## Probe retrieval anatomy — what reached the model

**Planted terms present in the rendered LTM block:**

| Domain | Treatment Q11 | Control Q11 |
|---|---|---|
| civil | present | present |
| art | **present** | absent |
| monetary | **present** | absent |
| marine | **present** | absent |

The treatment received material from all four domains at both probes. The
control received one domain at Q11 and three at Q14.

**And the treatment still scored Q11 = 0.0.** Its answer enumerated all four
subject areas, but populated Renaissance art with `1450–1510` and generic
Renaissance patrons, and monetary policy with ECB and Bank of Japan figures that
were never in this conversation — while `The Annunciation of Forlì`, `Melozzo`,
`1483`, `Taylor Rule` and `Dr. Priya Mehta` sat in its own context window.

The failure moved. Study 006 could not have enumerated four domains from what it
received. Study 007 could have, and did not.

## Context size

| | Peak tokens | % of 50,176 |
|---|---:|---:|
| Study 006 treatment | 12,169 | 24.3% |
| Study 007 control | 12,169 | 24.3% |
| Study 007 treatment | **16,916** | **33.7%** |

Under the replay gate's 60% limit and the 80% alert. The replay projected 13,741;
the actual 16,916 is higher because the projection assumed Study 006's non-LTM
remainder, and the treatment's longer answers enlarge the recent-context block.

## Determinism and cross-arm equality

Turns 1–31 are byte-identical between arms; the first divergence is turn 32, the
first turn after the dream pass at 31 gives the treatment a non-empty LTM to
budget over. 90 of 121 turns differ, which is the retrieval policy's footprint.

## Minimum-viable C (offline, observational)

Swept on Study 005's preserved raw store: **C = 40** is the smallest cap still
forming 4/4, against the shipped C = 50. Amendment 001 chose 50 as sufficient
rather than minimal and landed with about 20% headroom. C = 3, the value Study
006 carried in from Study 005, forms 0/4 — reproducing the original replay-gate
failure from a different direction. **C is not changed in this study.**
