# Duplication and Baseline Audit

## Scope and integrity

This was a read-only diagnostic. No inference calls were made, no server process
was contacted or reconfigured, and nothing under `experiments/study_010/` was
read or written. The only writes are this report and the two requested CSVs under
`experiments/analysis/`.

The audit hash-registered every file under Studies 002, 007, and 009 before
analysis and re-hashed the same inventory after producing the outputs. Final
results appear in **Hash verification** below.

## 1. Retrieval-budget log semantics

**Answer: `retrieval_budget.csv.selection` is logged after containment dedup and
refill accounting.** In the code that produced the accepted Study 007 run,
`arbitrate_budgeted` receives the union of recent and K-only STM source episode
IDs (`src/memory/retrieval_engine.py` at commit `f69b3c5`, lines 144-155).
`arbitrate_budgeted` excludes candidates using `episode_key(candidate)` before
budget selection (`src/memory/arbitration.py` at commit `b146967`, lines 67-86).
The runner then serializes `selection.selected` into `budget_selection`
(`src/runners/iterative_runner.py` at `f69b3c5`, lines 131-164), and the writer
writes that field to the CSV (`src/observability/file_writer.py` at `f69b3c5`,
lines 473-498).

Therefore duplication is intentionally invisible in `selection`; the CSV's
`containment_drops` records candidates removed before selection. Task 2 uses the
rendered blocks and their source IDs, not `selection` alone.

## 2. LTM versus STM duplication

`stm_ltm_overlap.csv` contains all 121 turns. In that CSV, `stm_episodes` is the
distinct union rendered through `<recent_context>` and `<retrieved_stm>`;
`ltm_chars` is the sum of serialized LTM `<episode>` elements, excluding only the
outer block wrapper and inter-record line breaks. Thus `duplicate_chars +
unique_chars = ltm_chars`. The requested Jaccard is LTM source IDs versus that
rendered STM/recency union.

| turn | ltm_records | ltm_chars | stm_episodes | overlap_count | jaccard | duplicate_chars | unique_chars | containment_drops | refills |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 120 | 7 | 33487 | 10 | 0 | 0.000000 | 0 | 33487 | 5 | 0 |
| 121 | 8 | 34132 | 10 | 0 | 0.000000 | 0 | 34132 | 5 | 0 |

Means over turns 32-121: LTM records 7.656, LTM record
characters 33131.4, rendered STM/recency episodes
10.167, overlap 0.000, Jaccard
0.000000, duplicate characters 0.0,
unique characters 33131.4, containment drops
5.056, and refills 0.000.

The separate LTM-versus-`<retrieved_stm>` overlap is also zero at turns 120 and
121; `<retrieved_stm>` is absent at both because K produced no K-only survivors.
The prominent defect condition does **not** occur: containment drops are
5 and 5, while
post-dedup rendered overlap is zero. The exact key is source episode ID via
`episode_key(candidate)`, not span offsets or text containment.

Turn 120 source-ID sets:

- LTM: `761e828b-48bb-4424-9d65-e17ab7e6b813`, `7f272a17-c445-4c60-919b-8d02d3e7acb9`, `908b8c5e-66f8-41d1-b875-63a431b9ff4b`, `98872452-010e-45d4-965b-c34e338812b0`, `b135a1a3-fb4e-4137-aea0-240a13704656`, `b8a6e4e7-a2ee-4665-9b86-a0889e7d0e3e`, `d64a8b9b-1895-4538-bae9-aea202414072`
- `<retrieved_stm>`: (empty)
- `<recent_context>`: `09c25f76-25d9-46f8-9f9b-0a5e21164b55`, `0fee8c56-7d2b-4fc1-a881-ac8159cb31fa`, `1dff4921-e025-4edb-91f9-60ff9b339fe1`, `7873628b-6aad-40c5-9261-46c88390a1ac`, `aee3ae6f-53b7-4821-a802-82b934fc96fa`, `b1b7db04-1a23-4b41-9d88-4a777316b99a`, `bc31f99b-4a85-43d7-901a-54a402b8d505`, `d1297458-91d2-4d6c-b26e-199d73f48ca9`, `d12c8fea-6fdf-4a31-adbc-f9e5dc0bcf74`, `e7845997-379c-41bc-8dbc-ed9e3aa7ba8b`

Turn 121 source-ID sets:

- LTM: `0ab88810-df32-480c-add1-f8d80b77c580`, `1f9df644-68f9-4e68-b141-652ea1d2d99a`, `7cf5ead9-ae4f-43ce-9961-c4a38de14c48`, `7f272a17-c445-4c60-919b-8d02d3e7acb9`, `908b8c5e-66f8-41d1-b875-63a431b9ff4b`, `b135a1a3-fb4e-4137-aea0-240a13704656`, `d64a8b9b-1895-4538-bae9-aea202414072`, `da21e4fc-71a6-4b2d-bee3-69caf2920a73`
- `<retrieved_stm>`: (empty)
- `<recent_context>`: `09c25f76-25d9-46f8-9f9b-0a5e21164b55`, `0fee8c56-7d2b-4fc1-a881-ac8159cb31fa`, `1dff4921-e025-4edb-91f9-60ff9b339fe1`, `7873628b-6aad-40c5-9261-46c88390a1ac`, `aee3ae6f-53b7-4821-a802-82b934fc96fa`, `b1b7db04-1a23-4b41-9d88-4a777316b99a`, `b58be92d-ffee-4983-8394-73624b87fc5a`, `bc31f99b-4a85-43d7-901a-54a402b8d505`, `d1297458-91d2-4d6c-b26e-199d73f48ca9`, `e7845997-379c-41bc-8dbc-ed9e3aa7ba8b`

Across all 121 turns, both the LTM-versus-K-only intersection and the
LTM-versus-(K-only union recency) intersection are zero after containment.

## 3. Context-gap reconciliation

Exact serialized character counts, including each block's opening/closing tags:

| turn | arm | pinned_rules | recent_context | retrieved_stm | retrieved_ltm | current_turn | whole prompt |
|---:|:---:|---:|---:|---:|---:|---:|---:|
| 120 | L | 592 | 26013 | 0 | 33548 | 289 | 60619 |
| 120 | S | 592 | 20018 | 0 | 0 | 289 | 21072 |
| 121 | L | 592 | 26742 | 0 | 34197 | 452 | 62160 |
| 121 | S | 592 | 20571 | 0 | 0 | 452 | 21788 |

Within LTM:

| turn | B_ltm used | utilization | serialized LTM | record text | tag/provenance markup |
|---:|---:|---:|---:|---:|---:|
| 120 | 31518 | 98.49% | 33548 | 31640 | 1908 |
| 121 | 31888 | 99.65% | 34197 | 32010 | 2187 |

- Turn 120: exact prompt gap 39,547 chars; LTM block 33,548 (84.8% of the gap), comprising 31,640 text chars (80.0%) and 1,908 markup chars (4.8%). The recent-context delta is +5,995 chars.
- Turn 121: exact prompt gap 40,372 chars; LTM block 34,197 (84.7% of the gap), comprising 32,010 text chars (79.3%) and 2,187 markup chars (5.4%). The recent-context delta is +6,171 chars.

Conclusion: the turn-120 gap is mostly, but not fully, the near-full 32,000-char
LTM payload plus its markup. Arm L's recent block is also larger because the arms'
generated responses diverged. The budget charges rendered episode content
(`ltm_chars_used`), while the prompt serializer adds episode tags, provenance
attributes, message tags, and the outer block.

## 4. Cost per marginal fact

“L-only” below means present in Arm L's probe prompt and absent from Arm S's,
matching the matrix's delivery columns. `answer_used` distinguishes facts the
model actually emitted. A fact can be carried by more than one LTM record.

| probe | L-only fact | answer_used | carrying LTM record(s) | rendered chars |
|:---:|---|:---:|---|---:|
| Q11 | Federal Reserve | yes | turn 69 / `a7a4ccb2-4159-5a5a-8272-251370cdf51b` | 6265 |
| Q11 | Dr. Kenji Watanabe | yes | turn 105 / `aaaae9a1-e02f-57b5-82f6-806f873defe9` | 4217 |
| Q11 | 600 | yes | turn 105 / `aaaae9a1-e02f-57b5-82f6-806f873defe9` | 4217 |
| Q11 | marine snow | yes | turn 105 / `aaaae9a1-e02f-57b5-82f6-806f873defe9` | 4217 |
| Q14 | The Annunciation of Forli | no | turn 58 / `1bd88291-f42d-53f7-bb74-44eefbea8975`; turn 59 / `6f872ed3-d10d-54de-bfff-e2fd18d2bf3f` | 6450 |
| Q14 | Melozzo da Forli | no | turn 58 / `1bd88291-f42d-53f7-bb74-44eefbea8975`; turn 59 / `6f872ed3-d10d-54de-bfff-e2fd18d2bf3f` | 6450 |
| Q14 | Cardinal Giuliano della Rovere | no | turn 59 / `6f872ed3-d10d-54de-bfff-e2fd18d2bf3f` | 3318 |
| Q14 | 1483 | no | turn 58 / `1bd88291-f42d-53f7-bb74-44eefbea8975`; turn 59 / `6f872ed3-d10d-54de-bfff-e2fd18d2bf3f` | 6450 |
| Q14 | Federal Reserve | yes | turn 69 / `a7a4ccb2-4159-5a5a-8272-251370cdf51b` | 6265 |
| Q14 | Dr. Kenji Watanabe | yes | turn 105 / `aaaae9a1-e02f-57b5-82f6-806f873defe9`; turn 102 / `ec255ba3-fdb9-585f-9466-a7a5ef658d55` | 8055 |
| Q14 | 600 | yes | turn 105 / `aaaae9a1-e02f-57b5-82f6-806f873defe9`; turn 102 / `ec255ba3-fdb9-585f-9466-a7a5ef658d55` | 8055 |
| Q14 | marine snow | no | turn 105 / `aaaae9a1-e02f-57b5-82f6-806f873defe9`; turn 102 / `ec255ba3-fdb9-585f-9466-a7a5ef658d55` | 8055 |

There are 12 L-only fact/probe pairs and
8 unique L-only facts. Summing each pair's carrying-record
cost gives 72,014 character-fact exposures, or
6,001.2 LTM characters per marginal fact/probe
delivery. Deduplicating shared records across both probes leaves
20,770 characters in 5 unique carrying records,
or 2,596.2 characters per unique L-only
fact. These are attribution costs, not claims that every character was necessary.

Restricting “delivered” to facts actually used in Arm L's answer leaves
7 fact/probe pairs: 41,291 character-fact exposures,
or 5,898.7 characters per used marginal
fact/probe. Across 4 unique used facts, the unique carrying
records cost 14,320 chars, or
3,580.0 per fact.

## 5. Pure-STM baseline audit

### Applied retrieval values

Both accepted implementations use `N_RETRIEVAL_CAP=10`,
`K_SIMILARITY_THRESHOLD=0.50`, and `DECAY_RATE=0.1`, with
`exp(-0.1 * elapsed_hours)` decay. The effective values in runtime logs are:

| probe turn | Study 002 C N | Study 002 C K | Study 009 S N | Study 009 S K |
|---:|---:|---:|---:|---:|
| 116 | 10 | 5 | 10 | 2 |
| 119 | 10 | 0 | 10 | 0 |
| 120 | 10 | 5 | 10 | 0 |
| 121 | 0 | 0 | 10 | 0 |

Study 002 has no turn 121; its script/run ends at turn 120.

Complete applied sequences are encoded as `turn:N/K`:

**Study 002 C**

- Turns 1-20: `1:0/0, 2:1/1, 3:2/0, 4:3/0, 5:4/1, 6:5/1, 7:6/1, 8:7/1, 9:8/1, 10:9/1, 11:10/2, 12:10/0, 13:10/1, 14:10/1, 15:10/1, 16:10/0, 17:10/2, 18:10/1, 19:10/2, 20:10/3`
- Turns 21-40: `21:10/1, 22:10/3, 23:10/2, 24:10/0, 25:10/2, 26:10/1, 27:10/0, 28:10/0, 29:10/2, 30:10/1, 31:10/0, 32:10/0, 33:10/0, 34:10/0, 35:10/0, 36:10/0, 37:10/0, 38:10/0, 39:10/1, 40:10/1`
- Turns 41-60: `41:10/3, 42:10/0, 43:10/3, 44:10/1, 45:10/2, 46:10/1, 47:10/2, 48:10/2, 49:10/0, 50:10/2, 51:10/3, 52:10/0, 53:10/1, 54:10/0, 55:10/0, 56:10/2, 57:10/2, 58:10/2, 59:10/2, 60:10/1`
- Turns 61-80: `61:10/0, 62:10/0, 63:10/0, 64:10/0, 65:10/0, 66:10/0, 67:10/0, 68:10/0, 69:10/1, 70:10/0, 71:10/0, 72:10/0, 73:10/0, 74:10/0, 75:10/0, 76:10/1, 77:10/2, 78:10/0, 79:10/2, 80:10/2`
- Turns 81-100: `81:10/0, 82:10/0, 83:10/0, 84:10/0, 85:10/1, 86:10/0, 87:10/0, 88:10/0, 89:10/0, 90:10/1, 91:10/0, 92:10/0, 93:10/0, 94:10/0, 95:10/0, 96:10/0, 97:10/0, 98:10/0, 99:10/0, 100:10/0`
- Turns 101-120: `101:10/0, 102:10/0, 103:10/0, 104:10/0, 105:10/0, 106:10/1, 107:10/0, 108:10/0, 109:10/0, 110:10/1, 111:10/0, 112:10/2, 113:10/2, 114:10/3, 115:10/3, 116:10/5, 117:10/5, 118:10/0, 119:10/0, 120:10/5`

**Study 009 S**

- Turns 1-20: `1:0/0, 2:1/1, 3:2/0, 4:3/1, 5:4/2, 6:5/2, 7:6/2, 8:7/2, 9:8/2, 10:9/1, 11:10/2, 12:10/2, 13:10/4, 14:10/2, 15:10/4, 16:10/0, 17:10/4, 18:10/5, 19:10/2, 20:10/6`
- Turns 21-40: `21:10/5, 22:10/7, 23:10/5, 24:10/1, 25:10/6, 26:10/3, 27:10/3, 28:10/1, 29:10/3, 30:10/3, 31:10/0, 32:10/0, 33:10/0, 34:10/0, 35:10/0, 36:10/0, 37:10/0, 38:10/0, 39:10/0, 40:10/0`
- Turns 41-60: `41:10/0, 42:10/0, 43:10/1, 44:10/0, 45:10/0, 46:10/0, 47:10/0, 48:10/0, 49:10/0, 50:10/0, 51:10/0, 52:10/0, 53:10/0, 54:10/0, 55:10/0, 56:10/2, 57:10/1, 58:10/1, 59:10/1, 60:10/1`
- Turns 61-80: `61:10/0, 62:10/0, 63:10/0, 64:10/0, 65:10/0, 66:10/0, 67:10/0, 68:10/0, 69:10/0, 70:10/0, 71:10/0, 72:10/0, 73:10/0, 74:10/0, 75:10/1, 76:10/1, 77:10/0, 78:10/0, 79:10/1, 80:10/0`
- Turns 81-100: `81:10/0, 82:10/0, 83:10/0, 84:10/1, 85:10/0, 86:10/1, 87:10/0, 88:10/0, 89:10/0, 90:10/0, 91:10/0, 92:10/0, 93:10/1, 94:10/0, 95:10/0, 96:10/0, 97:10/1, 98:10/0, 99:10/2, 100:10/0`
- Turns 101-120: `101:10/1, 102:10/1, 103:10/2, 104:10/1, 105:10/1, 106:10/2, 107:10/1, 108:10/1, 109:10/1, 110:10/1, 111:10/1, 112:10/4, 113:10/5, 114:10/1, 115:10/1, 116:10/2, 117:10/3, 118:10/1, 119:10/0, 120:10/0`
- Turns 121-121: `121:10/0`

Study 002 used topic assignment threshold 0.50, consolidation every 10 episodes,
and merge threshold 0.60. Study 009 used topic threshold 0.45, consolidation
every 10, merge threshold 0.45, plus the later domain-purity guard and
transition-aware consolidation. Retrieval remained global across episodes, so
these topic changes alter labels/consolidation but do not cap the N or K pools.

### Retrieved episode curve

Counts and serialized episode-element characters (wrappers excluded):

| turn | Study 002 C episodes | Study 002 C chars | Study 009 S episodes | Study 009 S chars |
|---:|---:|---:|---:|---:|
| 1 | 0 | 0 | 0 | 0 |
| 10 | 9 | 32808 | 9 | 17824 |
| 20 | 11 | 41491 | 12 | 26442 |
| 30 | 10 | 37408 | 10 | 21037 |
| 40 | 11 | 42303 | 10 | 20933 |
| 50 | 12 | 46517 | 10 | 21352 |
| 60 | 11 | 38716 | 11 | 23166 |
| 70 | 10 | 37770 | 10 | 20708 |
| 80 | 12 | 41185 | 10 | 21409 |
| 90 | 11 | 41295 | 10 | 21037 |
| 100 | 10 | 37313 | 10 | 20600 |
| 110 | 11 | 41166 | 11 | 25205 |
| 116 | 14 | 46518 | 11 | 22130 |
| 119 | 10 | 37509 | 10 | 18575 |
| 120 | 14 | 44973 | 10 | 19943 |
| 121 | 0 | 0 | 10 | 20496 |

At the probe turns, Study 002 C rendered 14
episodes / 46,518 chars at Q5 and
10 / 37,509
at Q8. Study 009 S rendered 11 /
22,130 and
10 /
18,575, respectively.

Study 002 C peaked at **13,143 estimated tokens on turn
117** and measured **11,349** at turn 120. Study 009 S
peaked at **9,960 on turn 25** and measured
**5,233** at turn 120. Thus the “about 13k” recollection is directionally
right for Study 002's peak, but turn 120 was lower.

### Q5 and Q8 source delivery

- Q5, turn 116, source turn 56: Study 002 C
  **did** render
  the source episode; Study 009 S
  **did not**.
- Q8, turn 119, source turn 101: Study 002 C
  **did not** render
  the source episode; Study 009 S
  **did not**.

### STM-path commit history

Every retrieval/assembly-affecting change between the Study 002 accepted run
(`fbdcfc6`) and Study 009 composition (`f901bda`) is:

| commit | change and delivery effect |
|---|---|
| `5f5421e` | Runner consumes the retrieval engine's constructed prompt, enabling pinned rules; N/K selection unchanged. |
| `7260d3d` | Consolidation merge threshold lowered 0.60 to 0.45; global N/K pools unchanged. |
| `37e2d7b` | Topic assignment embedding changed to user-message embedding; affects labels, not global N/K eligibility. |
| `32377d7` | Added domain-purity/transition consolidation guards; no N/K cap or threshold change. |
| `25462b7` | Replaced flat history with ordered XML blocks: pinned rules, N recency, K-only STM, LTM, current turn; N takes precedence over K on intersection. |
| `c0c3ee2` | Added parallel LTM arbitration to the iterative treatment; raw N/K calculations remained unchanged. |
| `0b1f989` | Gave LTM placement precedence over recency for LTM survivors; treatment-only, absent from Study 009 S. |
| `5f11a45` | Added distilled-LTM provenance metadata; no STM selection change. |
| `b146967` | Added LTM containment/budget selection; no STM selection change. |
| `7cbc891` and `4a29540` | Added span-rendering identities/helpers for Study 008; no STM selection change. |
| `f901bda` | Extracted the same N/K equations and constants into a structurally minimal STM-only engine; retains N cap 10, K threshold 0.50, decay 0.1, N-first dedup, turn-order rendering. |

**Verdict: no committed N/K threshold, decay, cap, or eligibility change was
found that would reduce Study 009 S's STM delivery.** Assembly changed from flat
history to tagged N and K-only blocks, but it preserves the N-union-K episode set.
The live Study 009 trajectory nevertheless produced fewer K hits and much shorter
stored responses, so its realized context was smaller. That is a run/runtime
outcome, not evidence of a deliberately degraded STM baseline.

The 13.0 versus 10.5 score delta is not a controlled cross-study comparison.
Runtime/model and quantization, response budget, seed, generated-response
trajectory, and rater differ; those differences affect stored episode text,
embeddings, K hits, and later prompts.

## 6. Unformed-plant reachability

Current scoring is `(entities + 2*numerics)/words`, multiplied by 1.5 for user
spans. Eligibility is 4-60 words and at least one entity or numeric token; the
formation floor is `F=0.15`, and the run used `C=50`.

| plant | source | words | entities | numerics | density | weighted | rank | minimum C / status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| art_pigment | 56 | 28 | 1 | 0 | 0.035714 | 0.053571 | 316 | unreachable at any C (salience below F=0.15) |
| art_patron_role | 60 | 35 | 2 | 0 | 0.057143 | 0.085714 | 240 | unreachable at any C (salience below F=0.15) |
| monetary_taylor | 61 | 25 | 1 | 1 | 0.120000 | 0.180000 | 91 | 91 |
| monetary_fed | 62 | 39 | 2 | 0 | 0.051282 | 0.076923 | 208 | unreachable at any C (salience below F=0.15) |
| marine_photophores | 101 | 17 | 0 | 0 | 0.000000 | 0.000000 | unranked | unreachable at any C (fails entity/numeric eligibility) |
| marine_feeding | 102 | 21 | 1 | 0 | 0.047619 | 0.071429 | 89 | unreachable at any C (salience below F=0.15) |

Ranks are within the eligible candidate list for that topic/dream event before
the salience floor and cap. Four spans are technically eligible but below the
fixed floor, so increasing C alone cannot form them. `monetary_taylor` clears the
floor but ranks 91st, requiring C=91. `marine_photophores` is not ranked because
spaCy recognized neither an entity nor a numeric token in the exact source span.
The exact source text and all fields are in `unformed_plants_reachability.csv`.

## Missing or bounded evidence

No required task was estimated from absent artifacts. Study 002 preserves its
constructed prompts, metrics, snapshots, and database even though several are
git-ignored. Study 002 does not have turn 121, so no effective N/K value exists
for that turn. Historical source citations use immutable git blobs at the commits
that produced the relevant behavior.

## Hash verification

Pre/post verification passed with **zero mismatches** across **1,906 files**.

- Study 002: 769 files; aggregate manifest SHA-256 `574c72710ac21d9e1f3d576aa2a370af3aee6bc9fb21208d1fd7dc66d659b109`.
- Study 007: 751 files; aggregate manifest SHA-256 `2870985a7c51518bb9c3c773172fac5ef92c1fb574ea7bb265156bf675ccdf85`.
- Study 009: 386 files; aggregate manifest SHA-256 `c6b09459117de5641a4487b044f3fc8303b4f6992382d67c39d9e8cdf08965eb`.

Key directly analyzed artifacts:

| artifact | pre-analysis SHA-256 | post-analysis |
|---|---|---|
| `experiments/study_002/runs/run_001/iterative/logs/turns.jsonl` | `3dbdd37caee22fdfd457c7ca8f6b98d3e0581a160c8b9da237701d3277fda085` | match |
| `experiments/study_002/runs/run_001/iterative/metrics/K_values.csv` | `e4719b91bce8baa0bd1d31178060711b8f2462e00aa661b68eb43a830d7929bd` | match |
| `experiments/study_002/runs/run_001/iterative/metrics/model_performance.csv` | `f05aaed7b0693147245425675197df88e0e765f8c5c77b970f64425191506e5e` | match |
| `experiments/study_002/runs/run_001/iterative/metrics/N_values.csv` | `f779ca51bf7a2fbb997f077a35fbe36e9e913b520ac2b169f8e0fa8fc9a1b5e5` | match |
| `experiments/study_002/script.json` | `7bf8ef646e82c8ed0cf6442a791cf24eac1f8883cad53f95127a049b1ad26e5a` | match |
| `experiments/study_007/runs/study_007_full_001/condition_c/dream_analysis/span_salience.csv` | `71ef31f40a5103a646036798e41e9e4c97a188fb2765ac0be6fdba4d4327afe8` | match |
| `experiments/study_007/runs/study_007_full_001/condition_c/logs/ltm_context_episodes.csv` | `ad6e0ab8bacce5eb75e33d8b147a6703432d8ad541e5c167a37ef48191ab2f0a` | match |
| `experiments/study_007/runs/study_007_full_001/condition_c/logs/retrieval_budget.csv` | `756b64ab028da7992523af5b672f0418a2ea2d1a5cc2ddde5b47ba55008e7684` | match |
| `experiments/study_007/runs/study_007_full_001/condition_c/logs/turns.jsonl` | `22b8b0c52ef5042f496695715d7b546edec51c2db997df57c9cdf268f5947ba9` | match |
| `experiments/study_009/evaluation/fact_delivery_matrix.csv` | `7d1ffd3868703e4d920b9ee94cbec5c4f6d2a36cbb5e6e4a6d914e3e6eeb72c3` | match |
| `experiments/study_009/runs/study_009_full_001/arm_s/logs/turns.jsonl` | `b612d360310bcc38919eb50c51aae1956b1cb8986a025847ef95c5313fb8601c` | match |
| `experiments/study_009/runs/study_009_full_001/arm_s/metrics/context_sizes.csv` | `817ef602f599649f3e2c9b8b677d8f85f9be865c9fcfa93466467ed32e3028bc` | match |
| `experiments/study_009/runs/study_009_full_001/arm_s/metrics/K_values.csv` | `8f4f85e402426885fb5992f088a1968a0cc81a8a894763f84ef414f44258dd81` | match |
| `experiments/study_009/runs/study_009_full_001/arm_s/metrics/N_values.csv` | `82b0b40da1990f91c4520615c0ebabc16cbc0bffdd0614b19c716c5d4e27fdf5` | match |
