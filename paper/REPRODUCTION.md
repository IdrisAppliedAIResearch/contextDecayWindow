# PAPER-001 Appendix E — Reproduction

One headline number, reproduced end to end from committed data in a clean
environment. Verified on 2026-08-02 against branch `paper-001`.

## What is reproduced

From §5.1, and the load-bearing claim of Figure 2:

> The exact minimum for 14 of 17 breadth items is **5,058 characters across five
> episodes**, against a 32,000-character budget.

This is the number that makes the paper's central argument possible: capacity
was never the constraint, because the target cost a sixth of the budget while
deployed selection spent all of it for 6 of 17.

## Why this number and not the 12 of 17

The 12-of-17 selection result cannot be reproduced from committed data alone. It
needs per-episode embedding vectors, which live in a SQLite store that is
gitignored and was never committed, and regenerating them needs the carried
embedder, which is not in the repository either. §12 and `paper/notes/
EVIDENCE_INDEX.md` §3b record the same limitation for Figure 1.

The 5,058-character result has no such dependency. The renderer is a pure
function of episode text, so the payload can be rebuilt from the committed turn
log and checked against the committed hash. No model, no embedder, no network,
no database.

## Prerequisites

Python 3.11 or later, and a checkout of this repository. Nothing else.

## Steps

Create a clean environment and install the library:

```bash
python -m venv .venv-repro
```

```bash
.venv-repro/bin/pip install ./episodic
```

On Windows the second command is `.venv-repro\Scripts\pip install ./episodic`.

Run the check from the repository root:

```bash
.venv-repro/bin/python paper/reproduce_headline.py
```

## Expected output

```
turns rebuilt from the committed log: [90, 112, 113, 115, 118]
  [OK ] episode count: 5
  [OK ] serialized characters: 5058
  [OK ] payload SHA-256: fa97d1dab3883225e00da7bc16b4c86db1ecb86fb52f7a743ce30a0b59a46809

REPRODUCED  14 of 17 breadth items are available in 5,058 characters of a
32,000-character budget (15.8% of it), across 5 episodes.
```

Exit code 0 means reproduced.

## What the script actually does

1. Reads `experiments/components/retrieval_mechanism_ledger/artifacts/ar_001/
   achievability.json` for the committed answer: which five turns form the exact
   optimum, how many characters the payload should be, and its SHA-256.
2. Reads those five turns' user and assistant text from the committed turn log,
   `experiments/surveys/retrieval_bakeoff/tier6/runs/tier6_live_121_corrected_001/
   context_matched_stm/logs/turns.jsonl`.
3. Renders them through the installed package's serialization contract,
   `episodic._render.render_stm_payload`.
4. Compares the result's length and SHA-256 against the committed values.

The check is not circular: the turn log is the raw conversation record, and the
expected length and hash come from AR-001's committed result, which was produced
by different code in the source repository. If the extracted library's renderer
had drifted by a single character, step 4 would fail.

`_render` is private to the package because callers are meant to go through
`EpisodeStore.context()`. It is used directly here because reproducing a
committed payload means rendering a named set of episodes rather than running
retrieval over a store.

## Verification record

Run on 2026-08-02, Windows 11, Python 3.13, fresh virtual environment.

| Check | Result |
|---|---|
| Environment contained only `episodic` and its `numpy` dependency | confirmed via `pip list` |
| `episodic` resolved to site-packages, not the repository tree | confirmed via `episodic._render.__file__` |
| Episode count | 5, matching committed |
| Serialized characters | 5,058, matching committed |
| Payload SHA-256 | `fa97d1da…` matching committed |
| Exit code | 0 |

## What this does and does not establish

It establishes that the extracted library reproduces a committed payload
byte-for-byte, and that the paper's 5,058-character figure is traceable to
committed data by a reader with no access to this program's runtime.

It does not establish the selection results. Those are availability measurements
over a store whose vectors are not committed, and reproducing them needs the
embedder under the batched call shape described in §11.3. A reader who wants to
check those has the per-configuration outputs in
`experiments/components/retrieval_mechanism_ledger/artifacts/e005/` and the hash
index in `paper/CLAIM_TO_ARTIFACT.md`, but cannot regenerate them from source.
