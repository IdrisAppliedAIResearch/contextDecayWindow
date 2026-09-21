# AF-PRE-002 (Part 1): lexical event-marker probe — is anchor-ness lexically visible?

Status: REGISTERED BEFORE RUN (2026-09-20). Parent: AF-PRE-001 closed NO_SIGNAL
(`../bert_anchor/RESULTS_001_sample120.md`). Partition ruling unchanged: LoCoMo is
characterization only; no confirmation claim possible. No model loads; pure regex;
no LLM readers; reuses pinned artifacts and the sample-120 pool of AF-PRE-001.

## Motivation (from AF-PRE-001 evidence)
- CE (zero-shot MiniLM) did not beat BM25 on answer-bearing LoCoMo evidence turns
  (25 vs 29 of 120): nothing for a model to add there.
- On the E 17-anchor gap — event turns ("The meeting X review took place…") that
  contain none of the query's answer tokens — **every** arm, BM25 included, ranked
  top-1 wrong (anchor BM25-rank 108/140 in all 17).
- Hypothesis H1: anchors are **event-boundary turns**, and event-ness is lexically
  visible. H2: adding a deterministic event feature to the lexical floor improves
  anchor identification — the prerequisite before spending GPU on fine-tuning
  (AF-PRE-002 Part 2 exists only if H2 holds).

## Rule (final, frozen before scoring)
A turn's `family_count` = number of DISTINCT regex families matching (case-insensitive,
word boundaries). `HYBRID(turn) = BM25(query, turn) * (1 + family_count)`.
`EVENT-ONLY top-1` = earliest turn with maximal family_count.

- `EVENT_NOUN`: meeting(s), wedding, engagement, trip, vacation, holiday, honeymoon, party, concert, game, match, tournament, race, marathon, show, performance, festival, ceremony, graduation, birthday, anniversary, dinner, lunch, breakfast, picnic, interview, conference, workshop, reunion, event, visit, audition, exhibition, launch, opening, premiere, move, surgery, class
- `TAKE_PLACE`: took place, held at, occurred, happened, scheduled, hosted
- `MOTION`: went, go(es|ing), gone, traveled, traveling, flew, fly, drove, drive, rode, arrived, left, departed, off to, headed to, visited, visiting, dropped by, stopped by
- `ATTEND`: attend(ed|ing), participat(ed|ing), joined, signed up, registered, enrolled
- `STATE_CHANGE`: married, engaged, graduated, retired, hired, fired, adopted, bought, sold, purchased, opened, closed, launched, started, finished, completed, quit, resigned, promoted, moved, relocated, welcomed, released, premiered, debuted, won, lost, founded, set up
- `ANNOUNCE`: just got, just booked, just finished, just started, just bought, just adopted, guess what, big news, excited to announce, can't wait to share
- `TEMPORAL_SHIFT`: last (week|month|year|weekend|night|summer|spring|fall|winter|<weekday>), ago, yesterday, the day before, back in, previously, a few (days|weeks|months) (back|ago)

## Surfaces and bars

**S1 — E 17-anchor gap (fidelity, synthetic-templated).**
Rule: gate on family_count ≥ 1, rank survivors by quoted-name overlap with the
query (longest query-quoted token appearing in the turn). Bar: ≥ 16/17 top-1;
any miss investigated line-by-line before interpretation. Expectation stated:
near-perfect (the anchor line is the only meeting line naming the queried item) —
S1 validates the rule machinery, it cannot establish H2 (templated data).

**S2 — LoCoMo sample-120 coverage (H1 test).**
`anchor_event_rate − nonanchor_event_rate` (share of turns with family_count ≥ 1),
gold = earliest-evidence turn. Bar: H1 supported if difference ≥ +15 points;
also report per-family coverage and per-category (1–4) table.

**S3 — LoCoMo sample-120 HYBRID vs BM25 (H2 test).**
Same gold, same tie-break (earliest turn) as AF-PRE-001; BM25 reference is the
sealed 29/120. Paired McNemar exact. Bars:
- **H2 SUPPORTED**: HYBRID net ≥ +10 over BM25 and p < .05 → lexical event info
  is enough to open AF-PRE-002 Part 2 (fine-tune MiniLM with echo/meta hard negatives).
- **PARTIAL**: net > 0 but < 10 or p ≥ .05 → report, no Part 2.
- **NOT SUPPORTED**: net ≤ 0 → lexical event-ness adds nothing; event-boundary
  supervision (not lexicons) becomes the prerequisite.

EVENT-ONLY top-1 reported as context (no bar; expected weak — it ignores the query).

## Failures of nerve this design pre-commits to accepting
- If anchors are preference/answer turns rather than event turns (cat-4 dominant),
  S2 difference may be ~0 and H1 dies; AF-PRE-001's E finding then remains the only
  anchor-flavored evidence.
- TEMPORAL_SHIFT may fire on a third of chat turns; if it dominates coverage and
  adds no discrimination, it is reported as noise, not quietly pruned (rule frozen).
