# TC-012 Research Memory Update

TC-012 is complete with `NO_DYNAMIC_PROMPT_SIGNAL`; the residual arm is
pre-locked `RESIDUAL_BINDER_LIMITED`. Both recompute candidate cosine by matrix
multiplication after every ASPECT hop, keep frozen 80/20 BM25 mixing, and use
TC-011's 50/50 allocator and carried `.3` query anchor / `.5` recurrence.

Full CC80/static ASPECT/dynamic prompt/residual aspect combined is
771/749/720/753 at 16k and 819/810/787/810 at 32k. Breadth is 17/15/8/15 and
24/23/20/23. Dynamic prompt versus static ASPECT is 2 gains/31 losses and 3/26;
breadth 0/7 and 0/3. Growing selected context creates feedback drift rather
than useful reconsideration.

Residual aspect is +4/0 versus static at 16k and 1/1 at 32k, with no breadth
change, but Part 1 found it differs from static on only 146/871 and 71/871 sets;
median hops fall back to the original query. Do not report this as broad signal.
It only says the exact lexical binder is mostly unavailable.

Preflight: 3,484 control reproductions, 117,966 state updates, 2,236 cache hits,
zero misses, zero embedding/LLM calls, selection SHA `0409bb83...`. Full CC80
remains fallback; no tuning, reader, deployment or adoption authorized.
The final repository suite is 2,253 passed.
