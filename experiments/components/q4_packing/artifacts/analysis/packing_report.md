# AS-001 Q4 Packing Result

**Status:** PASS
**Decision:** Branch D - PRIMACY MECHANISM LIVE
**Design anchor:** `7c90235a`

## Point Estimate

| Budget | Fitted episodes | Serialized chars | Source chars | Rank 27 enters | Margin |
|---:|---:|---:|---:|---|---:|
| 32,000 | 9 | 31,742 | 31,067 | NO | -18 |

## Sensitivity

| Budget | Episodes | Serialized chars | Source chars | Rank 27 enters |
|---:|---:|---:|---:|---|
| 16,000 | 5 | 15,664 | 15,266 | NO |
| 20,000 | 6 | 19,500 | 19,033 | NO |
| 24,000 | 7 | 23,907 | 23,371 | NO |
| 28,000 | 7 | 26,037 | 25,500 | NO |
| 32,000 | 9 | 31,742 | 31,067 | NO |
| 36,000 | 10 | 35,643 | 34,899 | NO |
| 40,000 | 11 | 39,684 | 38,872 | NO |
| 48,000 | 13 | 47,503 | 46,552 | NO |
| 64,000 | 16 | 63,086 | 61,928 | NO |

## Integrity

- Historical reproduction: PASS; 15 episodes and 59,708 characters.
- Canonical mechanism seal: FAIL_MISSING_COMMITTED_DB; 264 of 265 mechanism files tracked; `study.db` was never committed.
- Tracked sealed blobs: PASS; zero SHA mismatches.
- Checkout-only newline mismatches: 2; all normalized equivalent.
- Turn-55 cosine: 0.12042197585105896 (< K=0.48).
- Q4 availability at 32k: turn 55 absent; all four facts present: NO.
- No generative inference call or score change.

## Verdict

Branch D: **PRIMACY MECHANISM LIVE**. A separately pre-registered CC-001 pinned-set study may be proposed.
