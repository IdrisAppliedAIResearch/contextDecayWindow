# DA-064 Scratchpad

## 2026-08-31 - Registration

- Immutable represented episodes first.
- Then exact contiguous-bigram occurrence episodes in query/source order.
- Preserve session and episode coordinates; one replaceable item at a time.
- Complete reachability >=.90 and p50 completion position <=32.
- Seal before episode answer-marker join.
- Zero model/embedder/cache calls.

## 2026-08-31 - Result

- Complete required-episode reachability 382/465 (.822); any 440/465.
- Pack prefix alone complete for 186.
- Last required position p50 18.5/p90 71; depth bar passes only conditionally.
- Coverage bar fails, so `NO_OCCURRENCE_COORDINATE_SIGNAL`.
- Coordinates help when present; next test fixed local dependency radius.
