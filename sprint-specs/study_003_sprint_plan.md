# Study 003 — Sprint Plan
## contextDecayWindow
**Idris Applied AI Research**
**Date:** July 2026
**Pre-registration:** `experiments/study_003/pre_registration.md`
**Task numbering:** S3-T-001 onward
**Sprint numbering:** S3_001–S3_008
**Revision note:** v2 — pre-commit review revisions. S3-T-011 gains the merge-relabel guard; S3-T-012 trigger verification moved to a synthetic mini-script (S3-T-012a); all ablation references corrected to 35 turns; boundary conditions aligned with pre-registration v2.

---

## Sprint S3_001
### Pre-Registration Commit + Bug Fixes
**Goal:** Commit the pre-registration to version control. Fix the two mechanical bugs from Study 002 that carry zero design risk and can land before any architecture work begins.

---

#### S3-T-001 — Commit pre-registration

Copy `study_003_pre_registration.md` to `experiments/study_003/pre_registration.md`. Commit to version control using the message: `"Study 003 pre-registration — contextDecayWindow [no implementation changes]"`. The `[no implementation changes]` clause is required — it makes the commit auditable as a clean pre-registration. Record the SHA. No other files change in this commit.

**Acceptance criteria:**
- `experiments/study_003/pre_registration.md` exists in the repo
- Commit SHA recorded and stored in the pre-registration header
- No implementation files touched in this commit

---

#### S3-T-002 — Fix propagation bug in runner.py

In Study 002, `assignment.consolidation` was never wired to `TurnRecord`. Consolidation passes ran and computed results but those results were never recorded. `consolidation_events.csv` has zero rows as a result.

Locate the section of `runner.py` where `TurnRecord` is assembled after each turn. Add the consolidation result from `assignment.consolidation` to the TurnRecord before it is written. Confirm `consolidation_events.csv` receives rows after the fix.

**Exact change:** Find where TurnRecord is written. Add:
```python
turn_record.consolidation = assignment.consolidation
```

**Acceptance criteria:**
- `consolidation_events.csv` contains rows after a short test run (5–10 turns)
- No other runner.py behavior changes
- Existing tests pass

---

#### S3-T-003 — Remove rules from system prompt

In Study 002, formatting rules were pre-loaded in the system prompt. This created a confound: the model perceived the rules as already known and did not tag Turn 1 as rule establishment. The detection mechanism had no signal to fire on.

Locate the system prompt construction in the codebase. Remove any pre-loaded formatting or behavioral rules from the system prompt. The rule store (pinned rules appended to constructed context windows) remains intact — only the system prompt pre-load is removed.

**What stays:** The rule detection mechanism. The rule store. The pinned rule injection into constructed context windows.

**What goes:** Any lines in the system prompt that describe formatting rules, behavioral constraints, or response style instructions that are also targets of the detection mechanism.

**Acceptance criteria:**
- System prompt contains no pre-loaded formatting or behavioral rules
- Rule store mechanism is untouched
- A short test run (5 turns with a rule-setting turn 1) shows the detection mechanism fires and records the rule

---

**Sprint S3_001 complete when:** Pre-registration SHA recorded, propagation bug patched, system prompt cleaned, all three acceptance criteria verified.

---

---

## Sprint S3_002
### Consolidation Threshold Change
**Goal:** Change the topic merge threshold from 0.60 to 0.45. Verify consolidation fires on a short run. This is the architectural fix for Study 002's 52-topic failure.

---

#### S3-T-004 — Update merge threshold configuration

Locate where the consolidation merge threshold is defined. This is likely a config constant, an argument default, or a hardcoded value in the topic consolidation logic.

Change:
```python
CONSOLIDATION_MERGE_THRESHOLD = 0.60  # or equivalent
```
To:
```python
CONSOLIDATION_MERGE_THRESHOLD = 0.45
```

If this value is set in a config file (e.g., `config.yaml`, `settings.py`, `.env`), update it there and confirm it propagates correctly to the consolidation logic.

**Acceptance criteria:**
- Merge threshold is 0.45 in exactly one canonical location
- No hardcoded 0.60 values remain in consolidation logic
- Config change confirmed via print/log statement in a short test run

---

#### S3-T-005 — Verify consolidation fires

Run 20 turns of the Study 002 script. Inspect the consolidation log after the run. (20 turns is sufficient here — this task verifies consolidation only, which fires every 10 episodes. LTM promotion is not under test in this sprint and cannot fire before ≈ turn 31.)

**Acceptance criteria:**
- `consolidation_events.csv` has at least one row (consolidation fired)
- No cross-domain merges visible in the log (e.g., civil engineering episode merged with Renaissance art episode)
- Topic count at turn 20 is lower than the Study 002 equivalent (Study 002 had 7 topics at turn 10 — expect fewer or comparable with consolidation active)

**If consolidation still does not fire:** Do not proceed to S3_003. Diagnose. Check whether the 0.50 assignment threshold is producing centroids too granular for even 0.45 to catch. Report findings before any further changes.

**If cross-domain merges appear:** Do not proceed to S3_003. Raise threshold to 0.48 or 0.50 and re-verify. Record the adjustment as a deviation from the pre-registered value and document the reason.

---

**Sprint S3_002 complete when:** Threshold confirmed at 0.45, consolidation fires in 20-turn test, no cross-domain merges, topic count trending correctly.

---

---

## Sprint S3_003
### LTM Schema and DB Migration
**Goal:** Design and implement the LTM store as a separate SQLite table. The schema must support all four filter scores, trigger metadata, and the episode embedding for future similarity search when LTM retrieval activates.

---

#### S3-T-006 — Design LTM schema

Create `experiments/study_003/ltm_schema.md` documenting the schema before any code is written.

Schema:

```sql
CREATE TABLE ltm_episodes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id          TEXT NOT NULL,           -- FK to STM episodes table
    promoted_at_turn    INTEGER NOT NULL,         -- turn number when promotion fired
    topic               TEXT NOT NULL,            -- consolidated topic label at promotion time
    trigger_type        TEXT NOT NULL,            -- 'all_or_nothing' or 'weighted_threshold'
    triggered_filter    TEXT,                     -- filter name if trigger_type = 'all_or_nothing', else NULL
    novelty_score       REAL NOT NULL,
    repetition_score    REAL NOT NULL,
    association_score   REAL NOT NULL,
    emotional_score     REAL NOT NULL,
    weighted_score      REAL NOT NULL,
    content             TEXT NOT NULL,            -- full episode content
    embedding           BLOB NOT NULL,            -- 1024-dim float32 vector (sqlite-vec)
    promoted_at         DATETIME NOT NULL         -- wall clock timestamp
);
```

Also create a promotion log table for observational analysis:

```sql
CREATE TABLE ltm_promotion_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    turn                INTEGER NOT NULL,
    topic               TEXT NOT NULL,
    episodes_evaluated  INTEGER NOT NULL,         -- how many STM episodes were evaluated
    episodes_promoted   INTEGER NOT NULL,         -- how many passed the threshold
    promotion_rate      REAL NOT NULL,            -- episodes_promoted / episodes_evaluated
    logged_at           DATETIME NOT NULL
);
```

Commit `ltm_schema.md` before writing any migration code.

**Acceptance criteria:**
- `experiments/study_003/ltm_schema.md` exists and committed
- Schema reviewed — all fields from the pre-registration are present
- No migration code written yet in this task

---

#### S3-T-007 — Implement DB migration

Write a migration script at `migrations/study_003_ltm_init.py` that creates both tables (`ltm_episodes`, `ltm_promotion_log`) in the existing SQLite database. The migration must be idempotent — running it twice does not error or duplicate tables.

Use sqlite-vec for the embedding column if the existing STM store uses sqlite-vec. Match the vector storage approach already in use.

**Acceptance criteria:**
- Migration runs without error on a fresh DB
- Migration runs without error a second time (idempotent)
- Both tables exist and are inspectable via sqlite3 CLI
- Embedding column accepts a 1024-dim float32 vector

---

#### S3-T-008 — Write LTM store interface

Create `memory/ltm_store.py` (or equivalent location matching the existing codebase structure). Implement:

```python
def promote_episode(episode_id, promoted_at_turn, topic, trigger_type,
                    triggered_filter, novelty_score, repetition_score,
                    association_score, emotional_score, weighted_score,
                    content, embedding) -> int:
    """Write a promoted episode to ltm_episodes. Returns the new row id."""

def log_promotion_event(turn, topic, episodes_evaluated,
                        episodes_promoted) -> None:
    """Write a summary row to ltm_promotion_log."""

def get_ltm_centroid() -> Optional[np.ndarray]:
    """Compute and return the mean embedding of all LTM episodes.
    Returns None if LTM store is empty."""

def get_ltm_episode_count() -> int:
    """Return total number of episodes in ltm_episodes."""
```

**Acceptance criteria:**
- All four functions implemented and importable
- `promote_episode` writes a correct row — verify via sqlite3 CLI inspection
- `get_ltm_centroid` returns None on empty store, returns a (1024,) ndarray when rows exist
- `log_promotion_event` writes a correct row to `ltm_promotion_log`

---

**Sprint S3_003 complete when:** Schema documented, both tables created, interface implemented and verified via manual inspection.

---

---

## Sprint S3_004
### Promotion Mechanism Implementation
**Goal:** Implement the four-filter scoring logic and the topic-change trigger with merge-relabel guard. Verify the trigger end-to-end on a synthetic mini-script before it ever runs against the real script. Wire promotion into the main conversation loop. This is the primary new component of Study 003.

---

#### S3-T-009 — Implement filter scoring functions

Create `memory/promotion_filters.py`. Implement each filter as a standalone function returning a float in [0.0, 1.0].

```python
def score_novelty(episode_embedding: np.ndarray,
                  ltm_centroid: Optional[np.ndarray]) -> float:
    """
    Novelty = 1 - cosine_similarity(episode_embedding, ltm_centroid).
    If ltm_centroid is None (empty LTM), return 1.0 (maximum novelty).
    Note: when LTM is empty, the all-or-nothing exception is suspended —
    novelty = 1.0 reflects a structural default, not high-intensity encoding.
    Weighted threshold evaluation still applies.
    """

def score_repetition(retrieval_count: int, max_count: int = 5) -> float:
    """
    Repetition = min(retrieval_count / max_count, 1.0).
    Retrieval count is scoped to the episode's home-topic window.
    5 or more retrievals in that window = 1.0.
    """

def score_association(episode_embedding: np.ndarray,
                      ltm_centroid: Optional[np.ndarray]) -> float:
    """
    Association = cosine_similarity(episode_embedding, ltm_centroid).
    If ltm_centroid is None (empty LTM), return 0.0.
    """

def score_emotional_valence(episode_content: str,
                             inference_client) -> float:
    """
    LLM scoring call. Prompt:
    'Score the following text for emotional significance on a scale from
    0.0 to 1.0. Emotional significance includes fear, joy, anger, stress,
    excitement, grief, or surprise. Return only a single float and nothing
    else.'
    Parse the response as a float. Clamp to [0.0, 1.0].
    On parse failure, return 0.0 and log a warning.
    """
```

**Weights (pre-registered — do not change):**
```python
WEIGHTS = {
    "novelty":      0.35,
    "repetition":   0.30,
    "association":  0.20,
    "emotional":    0.15,
}
WEIGHTED_THRESHOLD = 0.60
ALL_OR_NOTHING_THRESHOLD = 0.90
```

**Acceptance criteria:**
- All four functions return floats in [0.0, 1.0]
- `score_novelty` returns 1.0 when ltm_centroid is None
- `score_association` returns 0.0 when ltm_centroid is None
- `score_emotional_valence` does not raise on malformed LLM output — logs warning and returns 0.0
- Unit tests for `score_novelty`, `score_repetition`, `score_association` (no LLM required)

---

#### S3-T-010 — Implement promotion decision logic

Add to `memory/promotion_filters.py`:

```python
def evaluate_promotion(novelty: float, repetition: float,
                       association: float, emotional: float,
                       ltm_is_empty: bool = False
                       ) -> Tuple[bool, str, Optional[str]]:
    """
    Returns (should_promote, trigger_type, triggered_filter).

    All-or-nothing check first (suspended when ltm_is_empty=True):
    If not ltm_is_empty and any single score >= ALL_OR_NOTHING_THRESHOLD:
        return (True, 'all_or_nothing', filter_name)

    Weighted threshold:
    weighted_score = (0.35 * novelty) + (0.30 * repetition)
                   + (0.20 * association) + (0.15 * emotional)
    if weighted_score >= WEIGHTED_THRESHOLD:
        return (True, 'weighted_threshold', None)

    return (False, '', None)
    """
```

**Acceptance criteria:**
- All-or-nothing fires before weighted check (when ltm_is_empty=False)
- All-or-nothing suppressed when ltm_is_empty=True — for every filter, including emotional
- Weighted score computed correctly
- Returns correct tuple in all three cases (all-or-nothing, weighted pass, reject)
- Unit test: (0.95, 0.0, 0.0, 0.0), ltm_is_empty=False → (True, 'all_or_nothing', 'novelty')
- Unit test: (0.95, 0.0, 0.0, 0.0), ltm_is_empty=True → weighted: 0.35×0.95=0.3325 < 0.60 → (False, '', None)
- Unit test: (1.0, 0.0, 0.0, 0.0), ltm_is_empty=True → weighted: 0.35 < 0.60 → (False, '', None)
- Unit test: (1.0, 0.60, 0.0, 0.50), ltm_is_empty=True → weighted: 0.35+0.18+0.0+0.075=0.605 → (True, 'weighted_threshold', None)
- Unit test: (0.0, 0.0, 0.0, 0.95), ltm_is_empty=True → suspension applies to emotional too → (False, '', None)
- Unit test: (0.70, 0.60, 0.50, 0.40) → compute manually and verify

---

#### S3-T-011 — Implement topic-change trigger with merge-relabel guard

**Design note (sequencing):** Topic change cannot be detected until the first episode of the new topic has been stored and consolidated — detection compares the current episode's consolidated topic against the previous episode's. The trigger therefore fires immediately *after* the incoming topic's first episode is stored and its consolidation pass completes. The incoming episode is excluded from the outgoing batch.

**Design note (merge-relabel guard):** Consolidation merges can rename the consolidated label of existing episodes. A label change caused by relabeling is not a topic transition and must not fire promotion. Resolve both the previous and current episodes' topics through the consolidation mapping to their canonical cluster identity before comparing. Fire only when the two canonical identities differ. Raw label-string comparison is insufficient once merges are active — and 0.45 makes merges active for the first time in this study.

In the main conversation loop, after each episode is stored and consolidated, run the guarded topic-change check. If a genuine transition is detected, gather all STM episodes belonging to the outgoing consolidated topic, run `evaluate_promotion` on each, and write promoted episodes to the LTM store.

```python
def run_promotion_at_topic_change(
    outgoing_topic: str,
    stm_episodes: List[Episode],
    ltm_store: LTMStore,
    inference_client,
    current_turn: int
) -> PromotionSummary:
    """
    Evaluate all STM episodes from outgoing_topic for LTM promotion.
    1. Snapshot LTM centroid ONCE before evaluation begins (held fixed for batch).
    2. Determine ltm_is_empty from current LTM episode count.
    3. Score each episode on all four filters against the snapshot centroid.
    4. Call evaluate_promotion for each episode.
    5. Write all promoted episodes via ltm_store.promote_episode().
    6. Update LTM centroid AFTER all batch writes are complete.
    7. Log the promotion event via ltm_store.log_promotion_event().
    Return a PromotionSummary for logging.
    """
```

**Acceptance criteria:**
- Trigger fires exactly once per genuine topic transition (not per episode)
- Trigger does NOT fire on consolidation merge/relabel events (unit test with a mocked consolidation mapping: previous episode relabeled, same underlying cluster → no fire)
- All STM episodes from the outgoing topic are evaluated — none skipped; the incoming topic's first episode is excluded
- Promoted episodes appear in `ltm_episodes` table immediately after trigger fires
- `ltm_promotion_log` receives one row per topic change event
- Trigger does not fire on the first topic (no outgoing topic to evaluate)
- Merge-relabel events ignored by the guard are counted and logged (feeds the "merge-relabel events" observational measure)

---

#### S3-T-012 — Wire promotion logging for observational analysis

The following fields must be logged to disk after each run for post-run observational analysis. Write to `experiments/study_003/runs/run_001/ltm_analysis/` (and equivalent paths for test runs):

- `promotion_events.csv` — one row per promotion event (topic change): turn, outgoing_topic, episodes_evaluated, episodes_promoted, promotion_rate
- `episode_scores.csv` — one row per evaluated episode: episode_id, topic, novelty, repetition, association, emotional, weighted_score, promoted (bool), trigger_type
- `filter_triggers.csv` — one row per promoted episode: episode_id, trigger_type, triggered_filter (null if weighted)
- `merge_relabel_events.csv` — one row per consolidation relabel correctly ignored by the trigger guard: turn, old_label, new_label

**Acceptance criteria:**
- Logging code paths exist for all four files and produce headers + rows when the corresponding events occur
- Verified end-to-end in S3-T-012a (synthetic mini-script), not against the real script — the real script's first topic change is at ≈ turn 31, beyond short-test range

---

#### S3-T-012a — Synthetic mini-script trigger verification

Verify the full promotion pipeline end-to-end without waiting for the real script's turn-31 topic change. Create `experiments/study_003/tests/synthetic_trigger_script.json`: a ~12-turn script with two clearly distinct topics switching at turn 6 (e.g., 5 turns cooking, then 7 turns astronomy), with at least one repeated/retrieved fact in topic 1 so the repetition filter has signal.

Run it through the full Study 003 architecture (real embeddings, real consolidation, real LLM emotional scoring — no mocks). This is a mechanism test, not a study artifact — the synthetic script is test fixture only and never touches run data.

**Acceptance criteria:**
- Topic change detected at the scripted switch; trigger fires exactly once
- All topic-1 episodes evaluated; topic-2 first episode excluded from the batch
- Empty-LTM path exercised: novelty = 1.0, association = 0.0, all-or-nothing suspended for the first batch
- `ltm_episodes` and `ltm_promotion_log` populated with all fields (inspect via sqlite3 CLI)
- All three observational CSVs written with correct rows (`merge_relabel_events.csv` may be header-only if no merge occurred)
- Centroid is None before the batch, non-None after (verify via `get_ltm_centroid`)

---

**Sprint S3_004 complete when:** All four filter functions implemented and unit-tested, promotion decision logic verified (including empty-LTM emotional suspension), topic-change trigger wired with the merge-relabel guard, and the synthetic mini-script verification passes end-to-end.

---

---

## Sprint S3_005
### Pre-Run 35-Turn Ablation
**Goal:** Run the mandatory 35-turn ablation against the real Study 002 script. Verify every item on the pre-run checklist before the full 120-turn run is authorized. This sprint produces a go/no-go decision — not a result.

---

#### S3-T-013 — Set CUDA PATH and run GPU speed test

Before any model inference:
- Verify CUDA PATH is set permanently in system environment variables (not per-session)
- Run GPU speed test: generate 200 tokens with Qwen3.6 27B Q6_K
- Record tokens/sec

**Acceptance criteria:**
- Speed test returns > 30 tok/s
- If < 30 tok/s: stop. Do not proceed. Diagnose VRAM or CUDA configuration before continuing.

---

#### S3-T-014 — Run 35-turn ablation

Run turns 1–35 of the Study 002 script using the Study 003 architecture (all fixes applied, LTM write path active). 35 turns is the minimum required to reach the first topic change (≈ turn 31) and verify LTM promotion fires. Do not run fewer than 35 turns.

After the run, inspect and document:

| Check | Expected | Actual | Pass? |
|-------|----------|--------|-------|
| GPU speed | > 30 tok/s | | |
| Consolidation fires | At least once | | |
| Topic count at turn 35 | Trending toward ≤ 20 pace | | |
| Cross-domain merges | Zero | | |
| LTM promotion fires | At topic change (≈ turn 31) | | |
| No spurious promotion on merge/relabel | Zero guard violations | | |
| LTM schema populated | All fields present in ltm_episodes | | |
| Rule detection fires | Turn 1 tagged without system prompt pre-load | | |
| `consolidation_events.csv` | Has rows | | |
| `episode_scores.csv` | Has rows | | |
| `ltm_promotion_log` | Has one row for the topic change | | |

Fill in the Actual column and Pass/Fail for each row. Document this table in `experiments/study_003/ablation/ablation_report.md`.

**Acceptance criteria:**
- All 11 checks pass
- Ablation report written and committed
- If any check fails: stop, diagnose, fix, re-run ablation from scratch

**Do not proceed to S3_006 until all 11 checks pass.**

---

#### S3-T-015 — Go/no-go decision

Based on the ablation report, make an explicit go/no-go decision. Write one line to the ablation report:

```
DECISION: GO — all 11 checks passed. Full 120-turn run authorized.
```

or

```
DECISION: NO-GO — [check name] failed. Reason: [description]. Fix required before proceeding.
```

Commit the ablation report with this decision line before touching any run code.

---

**Sprint S3_005 complete when:** Ablation report committed with GO decision and all 11 checks passing.

---

---

## Sprint S3_006
### Full 120-Turn Run
**Goal:** Execute the full Study 003 run against the Study 002 script. Log everything. Do not score during the run.

---

#### S3-T-016 — Prepare run directory

Create `experiments/study_003/runs/run_001/`. Subdirectory structure:

```
run_001/
  logs/
    runner.log
    consolidation_events.csv
    topic_assignments.csv
    k_retrieval_events.csv
  ltm_analysis/
    promotion_events.csv
    episode_scores.csv
    filter_triggers.csv
    merge_relabel_events.csv
  condition_c/
    responses.md       (model responses, turn by turn)
    context_sizes.csv  (token count per turn)
    rubric/
      scores.md        (filled in S3_007)
      responses.md     (probe responses, filled in S3_007)
```

**Acceptance criteria:**
- Directory structure created
- All log file handles open and writing before turn 1 begins

---

#### S3-T-017 — Execute 120-turn run

Run the full 120-turn Study 002 script using Study 003 Condition C architecture.

**During the run:**
- Log every turn's context token count to `context_sizes.csv`
- Log every K retrieval event
- Log every consolidation event
- Log every topic assignment
- Log every LTM promotion event and every guarded merge-relabel event
- Write model responses turn-by-turn to `responses.md`

**Emotional valence call overhead:** At three topic changes × ~30 episodes per topic, approximately 90 additional inference calls are made at promotion time. These queue through the same asyncio.Lock as conversation turns. This is expected — do not attempt to parallelize or bypass the lock.

**Monitoring:** Do not interrupt the run to check results. However: if context size exceeds 20k tokens at any turn, note the turn number in the run log but continue. If the model produces empty or severely truncated responses on 3 or more consecutive turns, stop, log the turn numbers, and report before continuing.

**Do not:**
- Interrupt the run to check results outside of the monitoring criteria above
- Skip any turns
- Modify any architecture during the run

If the run crashes: log the crash turn and error. Diagnose before re-running. Do not partially score a crashed run.

**Acceptance criteria:**
- All 120 turns complete without crash
- `responses.md` has 120 entries
- `context_sizes.csv` has 120 rows
- All LTM log files populated (three promotion events expected)
- Peak context token count recorded

---

**Sprint S3_006 complete when:** 120-turn run complete, all logs written, no crashes.

---

---

## Sprint S3_007
### Rubric Scoring and Observational Analysis
**Goal:** Score the 13-question rubric manually. Analyze LTM observational data. Do not draw conclusions yet — record findings only.

---

#### S3-T-018 — Extract probe responses

From `condition_c/responses.md`, extract the model responses to the 13 rubric questions (turns 112–120 plus any mid-run probe turns). Write these to `condition_c/rubric/responses.md`, one question per section, clearly labelled Q1 through Q13.

**Acceptance criteria:**
- All 13 probe responses extracted and labelled
- No paraphrasing — exact model output only
- Truncation noted explicitly where it occurred (do not silently omit)

---

#### S3-T-019 — Score rubric

Score each of the 13 questions using the Study 002 rubric criteria. Scoring criteria are defined in `experiments/study_002/rubric_filled.md` — use that document as the authoritative reference. Do not reinterpret criteria based on Study 003 context. Record scores in `condition_c/rubric/scores.md`.

Scoring must be completed before any analysis of LTM data. This prevents LTM findings from influencing rubric interpretation.

| Question | Category | Score | Notes |
|----------|----------|-------|-------|
| Q1 | Cat 1 | | |
| Q2 | Cat 1 | | |
| Q3 | Cat 1 | | |
| Q4 | Cat 2 | | |
| Q5 | Cat 2 | | |
| Q6 | Cat 2 | | |
| Q7 | Cat 3 | | |
| Q8 | Cat 3 | | |
| Q9 | Cat 4 | | |
| Q10 | Cat 4 | | |
| Q11 | Cat 4 | | |
| Q12 | Cat 5 | | |
| Q13 | Cat 5 | | |
| **Total** | | **/13.0** | |

Commit scores before opening any LTM analysis files.

**Acceptance criteria:**
- All 13 questions scored
- Category totals computed
- Overall total computed
- Scores committed before LTM analysis begins

---

#### S3-T-020 — Evaluate success bars

Compare Study 003 scores against the three pre-registered bars:

| Bar | Criterion | Study 002 Baseline | Study 003 Score | Pass? |
|-----|-----------|-------------------|-----------------|-------|
| Bar 1 | Cat 2 >= 3.0/3.0 | 3.0/3.0 | | |
| Bar 2 | Overall >= 13.0/13.0 (analyze any failure by category per pre-reg caveat) | 13.0/13.0 | | |
| Bar 3 | Topic count ≤ 20 at turn 120 | 52 | | |

Record pass/fail for each bar. Do not adjust scores or reinterpret rubric criteria based on results.

---

#### S3-T-021 — LTM observational analysis

Using the LTM log files, compute and document the following in `ltm_analysis/analysis_report.md`:

**Promotion volume:**
- Total episodes evaluated across all topic changes
- Total episodes promoted
- Overall promotion rate (promoted / evaluated)
- Promotion count and rate per topic (civil engineering, Renaissance art, monetary policy, marine biology)

**Filter behavior:**
- Distribution of novelty scores across all evaluated episodes (min, max, mean, median)
- Distribution of repetition scores
- Distribution of association scores
- Distribution of emotional valence scores
- Distribution of weighted scores
- How many episodes triggered via all-or-nothing vs weighted threshold
- Which filter was the all-or-nothing trigger most frequently

**Trigger guard:**
- Count of merge-relabel events correctly ignored by the guard
- Confirmation that promotion event count equals genuine topic transitions (expected: 3)

**LTM store at run end:**
- Total episodes in LTM store
- STM → LTM promotion ratio (LTM count / total STM episodes)
- Topic with highest promotion rate
- Topic with lowest promotion rate

**Do not interpret findings as pass/fail.** Record what happened. Interpretation goes in the study report (S3_008). Per the pre-registration's interpretive scope note: filter-level findings are conditional on the script's properties — a quiet filter under this script is not evidence against the filter.

---

**Sprint S3_007 complete when:** Rubric scored and committed, success bars evaluated, LTM observational analysis documented.

---

---

## Sprint S3_008
### Study Report and Memory File Updates
**Goal:** Write the Study 003 complete report. Update both memory files. Close the study.

---

#### S3-T-022 — Write Study 003 report

Create `experiments/study_003/study_003_report.md`. Follow the structure established in Study 001 and Study 002 reports:

- Summary (result: VALIDATED / PARTIAL / FAILED)
- Research questions
- Changes from Study 002
- Method
- Results (rubric scores, success bar table)
- Discussion (one section per finding — rubric performance, consolidation fix, LTM observational findings)
- What I'd do differently
- Protocol notes (any engineering issues during the run)
- Limitations
- Next steps (Study 004 priorities)
- Appendix (file paths)

**The discussion section for LTM must cover:**
- Which filters fired most frequently and why that makes sense given the script content
- Promotion rate per topic and what drove the differences
- What the observational data suggests for LTM retrieval threshold design in Study 004
- Any unexpected behavior in the promotion mechanism, including trigger-guard activity

**Acceptance criteria:**
- All sections present
- Success bar table filled with actual scores and pass/fail
- LTM discussion based on observational data — no speculation beyond what the data shows
- Next steps section identifies Study 004's primary architectural addition (LTM retrieval read path)

---

#### S3-T-023 — Update memory files

Update `MUZAFFER_PROFILE.md` and `CLAUDE_CONTEXT.md`:

- Study 003 status: COMPLETE (with result)
- Rubric scores recorded
- LTM observational key findings summarized
- Study 004 planned section added (LTM read path as new component)
- Last updated timestamp updated

**Acceptance criteria:**
- Both files updated
- Study 003 no longer marked as planned/in-progress
- Study 004 section exists with at minimum: "New component: LTM retrieval read path. Fixes from Study 003: [to be determined after analysis]. Pre-registration not yet committed."

---

#### S3-T-024 — Close study

Final checklist before closing:

- [ ] Study 003 report committed
- [ ] Memory files updated and committed
- [ ] All run logs archived under `experiments/study_003/runs/run_001/`
- [ ] LTM analysis report committed
- [ ] Ablation report committed
- [ ] Decision record (`DECISION_consolidation_threshold_study003.md`) committed under `experiments/study_003/decisions/`
- [ ] Pre-registration SHA confirmed in report header

**Sprint S3_008 complete when:** All items checked. Study 003 closed.

---

---

## Summary

| Sprint | Scope | Output |
|--------|-------|--------|
| S3_001 | Pre-reg commit, bug fixes | SHA recorded, bugs patched |
| S3_002 | Consolidation threshold 0.45 | Consolidation fires, topic count trending correctly |
| S3_003 | LTM schema + migration | Two tables live, interface implemented |
| S3_004 | Promotion mechanism + synthetic trigger test | Four filters, guarded trigger, logging wired, end-to-end verified |
| S3_005 | Pre-run 35-turn ablation | Go/no-go decision documented |
| S3_006 | Full 120-turn run | All logs written, no crashes |
| S3_007 | Scoring + LTM analysis | Bars evaluated, observational report |
| S3_008 | Report + memory updates | Study closed |
