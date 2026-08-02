# CC-004 — Restart Persistence

**Pre-registration:** `CC_003_004_005_deployment_closeout.md` at `43588944`
**Branch:** `cc/004-persistence`
**Status:** PASS — P1–P6 green, suite 986

Closes `CC_001` O4.

## 1. The gap

The checkpoint path had run exactly once, in an incident: Study 010 arm L
resumed from its turn-500 checkpoint after the process was reaped at turn
597. A path that worked once under lab conditions is not a guarantee, and a
deployed agent restarts constantly.

## 2. The durability point, stated

§2.2.1 required that the durability point be specified and documented
rather than left implicit. It is now both, in the module docstring and in
an assertion:

> **When `append("assistant", ...)` returns, the episode is on disk.**

The store sets `synchronous=FULL` and `journal_mode=DELETE` explicitly on
every open. SQLite's own default for `synchronous` is already FULL, so this
changes nothing at runtime — that is the point. A durability guarantee that
rests on a library default is a guarantee nobody can audit, and a later
version of that default would silently retract it. Two tests read the
pragmas back.

The episode row and the clearing of the pending user message are one
transaction. That is what makes a kill mid-append leave the turn wholly
present or wholly absent, which P3 asserts directly.

## 3. Kills are real

The tests do not simulate a crash. A child interpreter is started, told to
append, and killed with `Popen.kill()` — `TerminateProcess` on Windows,
`SIGKILL` elsewhere. Neither runs handlers, flushes buffers, nor closes the
database. The child prints a marker only after its writes are acknowledged,
so the kill lands strictly after `append()` returned and the test measures
the stated durability point rather than a race.

Anything that survives that survived because SQLite put it on disk before
`append()` returned.

## 4. What changed

### 4.1 Corruption is refused at open

SQLite's journal makes a *torn write* recoverable. It does not make a file
damaged from outside the database recoverable, and such a file still opens
and still answers queries from the pages that survived. `PRAGMA
quick_check` now runs on every open and a failure raises `StoreCorruptError`
rather than serving from a damaged store. §2.2.4 asked that torn writes be
detected rather than silently accepted; this is the detection, at the one
moment a caller can still act on it.

### 4.2 `verify_embeddings()`

§2.2.3 asked that the embedding cache survive or be rebuilt
deterministically. **There is no cache.** Vectors live in the episode row,
so they survive by construction and there is nothing to rebuild — P4
asserts bit-identity across restart and re-derives every vector from its
own source text.

What remained unguarded was a stored vector that no longer corresponds to
its row: a bad migration, a partial restore, an edit through another
connection. `verify_embeddings()` re-embeds every episode and compares
bytes, raising `EmbeddingDriftError` on the first mismatch.

This is complementary to the H1 sentinel, not redundant with it, and
writing the test made the boundary explicit:

| Fault | Caught by | When |
|---|---|---|
| The embedder changed (artifact, runtime, call shape) | H1 sentinel | every open, one fixed string, O(1) |
| A stored vector no longer matches its own text | `verify_embeddings()` | on request, every episode, O(n) |

The first attempt at the drift test failed because the sentinel fired
first — which is the correct ordering, and is now asserted as such.

### 4.3 Errors are exported

`EpisodicError` and its subclasses are exported from the package root so
callers can catch them by name rather than by matching message text.

## 5. Tests

| # | Test | Certifies | Result |
|---|---|---|---|
| P1 | append n turns, kill, reopen: all n present and verbatim | durability | PASS |
| P2 | same query and budget pre/post restart: byte-identical block | **the core guarantee** | PASS |
| P3 | kill mid-append: turn wholly present or wholly absent; damaged file refused | crash consistency | PASS |
| P4 | vectors bit-identical after restart; drift detected | rebuild determinism | PASS |
| P5 | reopen under an altered config raises | config integrity | PASS |
| P6 | 100 restart cycles: no drift, no growth in open time or file size | repeated restart | PASS |

23 persistence tests; full suite 986, up from 963.

**P2 carries its content check.** §2.3 warns that byte-identical blocks are
also produced by two empty stores, so the paired test asserts the block is
non-empty, episode-bearing, over 500 characters, and contains the stored
text. Identity alone would pass on nothing.

**P3 also covers the legitimate half-turn.** A user message with no
assistant reply is *allowed* to persist — it is a pending turn, not a torn
write — and the test asserts it resumes correctly after restart rather than
being discarded.

## 6. Boundary

- P1 and P3 kill a process. They do not cut power. `synchronous=FULL` is
  what would carry the guarantee across a power loss or a lost storage
  connection, and that claim rests on SQLite's implementation, not on
  anything measured here.
- P6 runs 100 cycles on a store of 25 episodes. It catches an O(n)
  regression in open cost and file-size drift; it is not an endurance test,
  and its timing bound is deliberately loose enough to tolerate scheduler
  noise on a shared machine.
- The tests use a deterministic content-derived embedder, so they agree
  across processes without the carried model. That is what makes them
  suitable for a unit suite; it also means they certify the *store's*
  persistence behaviour and not the carried embedder's reproducibility,
  which is H1's job and CC-002's T5.
- `quick_check` is not `integrity_check`: it skips the index-consistency
  pass. It is what runs on every open, so it is what the cost had to be
  bounded by. A caller that wants the full check can run it.
