# HANDOFF — temporary

**Written 2026-08-13 for the agent picking this up next. Delete this file when
NF-003 is registered or the corpus decision is made; it is a note between
agents, not a program record.** Nothing in it is authoritative. Where it and a
committed artifact disagree, the artifact wins.

---

## 1. Read these first, in this order

1. `AGENTS.md` — the operating manual. **§4 standing rules, §7 Never, §9 Reading
   a Result.** §9 is recent and it is the one most likely to change how you
   work: this program stops studies often, and §9 is the difference between a
   finding and a tombstone.
2. `README.md` — everything below the `# For LLM Context` divider is the full
   record with numbers and artifact paths. Above the divider is for humans; do
   not add detail there (`AGENTS.md` §6, *README Structure*).
3. `experiments/components/biological_memory/nf_003/NF_003_PART1_RECORD.md` —
   the immediate open work.
4. `ERRATA.md` — before quoting any number, always.

## 2. Where the repository is

- Branch `study/nf-003-ranking-granularity`, which is **stacked on**
  `chore/readme-restructure` ([PR #56](https://github.com/IdrisAppliedAIResearch/contextDecayWindow/pull/56),
  open). If #56 merges first, rebase onto `main`. Nothing here depends on it
  except that you inherit the restructured README and the §6 guidance.
- `main` is at the PR #55 merge: DMR-004 closed, NF-001/002 closed, NF-003
  Part 1 committed, 14 integrity gates restored.
- **Suite: 1,757 passed, 0 failed.** Run it with
  `.\.venv\Scripts\python.exe -m pytest -q` (~130s). The system `python` on PATH
  has no pytest. Any failure you see is new — the historical "14 pre-existing
  failures" are gone and must not be reintroduced as an excuse.

## 3. The open decision, which is the user's and not yours

NF-003 Part 1 measured a large effect: ranking candidates at episode granularity
instead of inheriting a session's rank raises any-evidence recall on
LongMemEval from **396 to 445 of 470 — 49 gains, 0 losses, p < 1e-5, zero model
calls.**

It cannot be confirmed. **Every LongMemEval item has now been used by this
program**, and NF-002 carries `DEVIATION_001` for having printed holdout counts
before its bars were locked. There is no sealed subset left. A registration
written today inherits that ceiling and can only reach `CHARACTERIZED`.

Two tracks were proposed to the user, in parallel:

- **Track A — register and run NF-003 for the record**, accepting the
  `CHARACTERIZED` ceiling. Does not need authorization.
- **Track B — acquire a corpus this program has never touched**, so something in
  this line can finally be *confirmed*. **This needs the user's explicit
  authorization**, because it means bringing in a new external dataset. Do not
  fetch, download, or register against a new corpus until they say so. If they
  have not answered, ask once and proceed with Track A meanwhile.

## 4. If you are doing Track A

The design work is not started. What is already fixed and must not drift:

- The discriminator was **committed before the numbers existed**: the cosine
  rank of the true evidence episode, identified by LongMemEval's own
  `has_answer` turn flag. Median 2 of ~229 on items the previous arm reached;
  41 on the misses. That is what makes dilution the confirmed dominant
  mechanism rather than a story fitted afterwards.
- H2, similarity failure, survives as a genuine residual on **25 of 470** items
  whose evidence is deep even at episode granularity. No unit or packing change
  reaches them. Do not quietly fold them into the win.
- Mechanism code lives in `src/analysis/nf003_ranking.py`. `pack()` returns
  **both** `(sessions_touched, episodes_delivered)` — see §6.
- Registration requires **two dispositions fixed before the run** (§9.3): the
  `WORKS` bar and a separately numbered `CARRIES_SIGNAL` bar, both reachable in
  each direction under PF4. NF-002's are in `src/analysis/nf002_gates.py` as a
  worked example.
- PF1–PF10 are mandatory and the registration commit must contain **no
  implementation file**.

## 5. Also unblocked, if the NF line stalls

**DMR-002 and DMR-003 are runnable today.** A blocking review
(`experiments/components/biological_memory/deterministic_retrieval/DMR_ARC_BLOCKING_REVIEW.md`)
found they had been blocked in error: both consume the frozen DMR-001B former,
whose operating point DMR-001C confirmed on a sealed holdout, and neither needs
the boundary claim that failed. DMR-005 and DMR-006 remain blocked by their own
dependency lines.

## 6. Traps this program has hit more than once

These are not hypotheticals. Each cost real work here.

- **Unit mismatch.** The single most repeated failure. NF-003's own first pass
  reported a 45-item *regression* by comparing evidence episodes against
  evidence sessions; the truth was a 49-item gain. Count-based caps also break
  silently when the unit changes size — seven instances on record. Before
  comparing two numbers, say out loud what each one counts.
- **Printing a holdout figure is reading it.** A code comment saying `"NOT read
  for bars"` does not unsee it. That is what cost NF-002 its confirmatory
  standing. Compute development and holdout statistics in **separate commands**,
  and do not run the holdout one until the registration is committed.
- **The live 13-point instrument has a 3.0-point band.** Five byte-identical
  replicates scored 8, 8, 8, 8, 11. Do not propose a live scored contrast to
  settle anything smaller, and do not cite the band to revive a fired bar.
- **The runtime is not bit-reproducible.** Same prompt, same seed, different
  answer. The program's byte-identical-rerun rule cannot be satisfied here.
  Offline counts and identities reproduce exactly; scores do not.
- **Embedding call shape changes the vector.** Same text in a different batch
  gives a different vector. Replay the call, not just the query. The CC-006
  cache is content-addressed, read-only, and **miss-is-fatal** by design — if it
  raises, do not "fix" it by embedding on the fly.
- **A blocking claim inherits no authority from age** (§9.1). DMR-001's stop was
  carried forward through two stages after the evidence beneath it had changed,
  and wrongly blocked two runnable ones.

## 7. Runtime facts

- Seed **5005**, llama.cpp on port **8080**, one slot, speculative decoding off.
  **Launch and poll the model server yourself**; do not ask the user to start it.
- Qwen3.6 27B UD-Q6_K_XL for inference, Qwen3-Embedding-0.6B for embeddings,
  SQLite + sqlite-vec for storage.
- Registered SHA-256 constants exist under **two incompatible line-ending
  conventions**. `.gitattributes` pins each hashed file to the rendering its own
  constant expects (400 LF, 59 CRLF). If you add a hashed artifact, pin it, and
  record which convention you hashed under.
