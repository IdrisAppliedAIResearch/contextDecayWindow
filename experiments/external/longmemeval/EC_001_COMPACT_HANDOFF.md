# EC-001 compact handoff

**Branch:** `ec/001-longmemeval`

**Manual-switch amendment:** `c2bd4b52ee0904c15135efcaf099e094da21b56c`

**Governing two-model amendment:** `b80bd8b32a86771dbaa4ba1f2fb8faa0eaae074d`

**Current status:** waiting for manual switch to **GPT-5.4**

**Exact resume phrase:** `EC001 RESUME C1 GPT-5.4 SWITCHED`

After compaction, read only:

1. root `AGENTS.md`;
2. `amendments/AMENDMENT_009_codex_agent_evaluators.md`;
3. `amendments/AMENDMENT_010_two_hosted_replacements.md`;
4. `EC_001_CODEX_AGENT_RUNTIME_RECORD.json`;
5. `EC_001_CODEX_AGENT_CHECKPOINT.json`;
6. `EC_001_CODEX_AGENT_RUNBOOK.md`.

Then verify the exact resume phrase and follow the runbook. Spawn the C1 child
with `fork_turns="none"` and omit both model and reasoning overrides so it
inherits GPT-5.4 with a fresh context.

Do not open the sealed identity map, prepare triggers, aggregate scores, or
read other rater outputs. Phi and Mistral are already committed rater passes.
GPT-5.4 is the third rater; GPT-5.5 is the later adjudicator.
