# Study D Part 1 extension 001 — runtime and budget feasibility

Status: development only; authorized by the user's end-to-end delegation. This extension is committed before its code or calls. No confirmatory data, answer scores or temporal treatment comparisons are opened.

## Question

Can the carried Qwen3.8 reader and exact tokenizer run serially, reproducibly and within context limits on the existing public baseline? The original draft's Qwen3.6 artifact is not assumed available; the locally verified Qwen3.8 artifact is a candidate reader, not a silent substitution in a locked registration.

## Frozen inputs and operations

Runtime file hashes are in `artifacts/part1/runtime_files.json`. Reader SHA is `bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372`; server SHA is `125e0938a280cba46c803a60178e51826203e030abacce03367a22108720f7ac`; embedder SHA is `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`.

Launch a dedicated localhost port 8097 with one 65,536-token slot, GPU layers all, Q8 key/value cache, flash attention, no context shift and no speculative decoding. Do not interrupt unrelated servers. Record launch command, PID, model identity and `/props`; stop only the process created here if a repair is necessary. Probe readiness before inference.

Use the existing HH-001 reader template and LV-002 closed-think suffix. Three small developer-authored source/query fixtures: explicit code lookup, two explicit dates with elapsed days, and an absent code. Each receives two successive identical calls at seed 5005, temperature .6, top_p .95, top_k 20, min_p 0, repetition penalty 1, presence penalty 0, cache_prompt false, output ceiling 512. Six maximum generation calls in this extension. Persist each full response before any next call; no retries after a persisted response. These are runtime/completeness fixtures, not outcome estimates or scorer calibration.

Compute exact tokenizer lengths on the prompts and store them. Require nonempty final text, natural completion before cap, and byte-identical paired responses. Failures characterize the candidate instrument; they do not establish a temporal mechanism outcome. A failed determinism or completeness check requires a new committed repair plan before further generation.

## Preflight

PF1 verified file inventory precedes launch; hash prompts before calls. PF2 record actual props and response stop fields rather than model aliases. PF3 require this commit and successful readiness before calls, persist before comparisons. PF4 both identity and nonidentity outcomes are possible; three nonempty prompts ensure a real tested population. PF5 prompt and response content hashes are comparison keys. PF6 prior server/model hashes are reproduced; the separate full frozen baseline replay remains mandatory. PF7 six serial calls test repeatability, not endurance or arbitrary server state. PF8 these tiny inputs cannot establish maximum-length completion; later corpus-specific checks remain required. PF9 byte identity can reproduce wrong answers and short completions can conceal long-prompt failure; neither is called reader accuracy. PF10 eventual full paired reader study remains mandatory. All checks report executed evidence, including failed branches.

## Budget decision to carry forward

Do not change the package's character packer merely to make the draft's token-language true. The completed registration must either explicitly use the existing 32,000-character retrieval allowance plus identical continuity in both arms, auditing exact tokens separately, or choose a separately identified prior token-budget baseline. Selection between those options follows the public behavior/replay evidence. No treatment can be implemented until that choice is recorded in the completed registration.
