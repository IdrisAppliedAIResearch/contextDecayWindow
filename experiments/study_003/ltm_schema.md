# Study 003 — Long-Term Memory Schema

**Status:** Schema design approved before migration implementation (S3-T-006).

Study 003 adds a write-only long-term memory (LTM) tier. Promoted episodes remain in the existing STM `episodes` table; this schema records their promotion metadata and supports later similarity retrieval without enabling LTM retrieval in this study.

## `ltm_episodes`

```sql
CREATE TABLE ltm_episodes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    episode_id          TEXT NOT NULL,
    promoted_at_turn    INTEGER NOT NULL,
    topic               TEXT NOT NULL,
    trigger_type        TEXT NOT NULL,
    triggered_filter    TEXT,
    novelty_score       REAL NOT NULL,
    repetition_score    REAL NOT NULL,
    association_score   REAL NOT NULL,
    emotional_score     REAL NOT NULL,
    weighted_score      REAL NOT NULL,
    content             TEXT NOT NULL,
    embedding           vec_float32(1024) NOT NULL,
    promoted_at         TEXT NOT NULL
);
```

`episode_id` identifies the unchanged STM source episode. `trigger_type` is either `all_or_nothing` or `weighted_threshold`; `triggered_filter` is populated only for the former. All four filter scores and the final weighted score are retained for observational analysis. The embedding uses the same 1,024-dimensional sqlite-vec representation as STM.

## `ltm_promotion_log`

```sql
CREATE TABLE ltm_promotion_log (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    turn                INTEGER NOT NULL,
    topic               TEXT NOT NULL,
    episodes_evaluated  INTEGER NOT NULL,
    episodes_promoted   INTEGER NOT NULL,
    promotion_rate      REAL NOT NULL,
    logged_at           TEXT NOT NULL
);
```

There is one log row per topic-change promotion event. `promotion_rate` is `episodes_promoted / episodes_evaluated`; the store interface records `0.0` when no episodes are evaluated to avoid division-by-zero ambiguity.

## Constraints and lifecycle

- The migration is idempotent and creates both tables only when absent.
- The schema intentionally does not remove, compact, or alter STM episodes.
- LTM retrieval remains inactive in Study 003; no LTM records are included in context construction.
- `promoted_at` and `logged_at` are UTC ISO-8601 timestamps.
