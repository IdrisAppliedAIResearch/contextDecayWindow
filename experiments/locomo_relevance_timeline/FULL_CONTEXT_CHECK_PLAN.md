# Selected versus full-conversation token check

User questions whether to delay the LoCoMo reader run because the anchor component is inactive and retrieval may approach full-context size. Pause registration and reader inference. No study reader or judge calls have occurred.

Compare all 1,986 selected native prompts with full-conversation prompts built from every frozen pair in the same source order, same date/dialogue metadata, same HH001 question and native template. Tokenize both at the same server build. No generation, new retrieval, selection tuning, scoring or gold inspection. Context capacity does not limit tokenization. The comparison is full context of the carried text-pair adapter, which omits separate image metadata and captions; do not call it a multimodal full transcript.

Report selected and full input token distributions, per-question retained ratios and saved tokens, per-conversation ranges, empty selections, count near full context (>=80%, >=90%, >=95%), and primary/category breakdowns. The allocation window is not input length. Include all questions, preserving occurrence identities. Use extrema and distribution values, not one longest input as a corpus summary.

Preflight: verify committed prompt/adapter hashes; reproduce every selected prompt from its selected IDs and exact question; verify full source order and same-template construction; all keys unique and complete; no generation route used; commit code before execution and outputs before interpretation. Existing E replay and cache gates stand. This is a descriptive size check, not an efficacy test. Keep full inference paused pending discussion of the narrowed test and anchor transfer.
