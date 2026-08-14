# NF-008 Registration Preparation Checklist

**Status:** `PREPARATION ONLY - NO REGISTRATION SHA`  
**Execution:** forbidden until every open item is resolved in a committed,
authorized pre-registration with PF1-PF10

## Inputs to freeze

- Corrected internal database and exact turn-120 Q11 text, with byte hashes.
- NF-006 selection seal and measurement artifact, with commit and SHA-256.
- Exact reconstructed C0 and T1 retrieval blocks and full prompt bytes.
- Reader weights, server build, launch command, GPU/runtime properties, seed,
  sampling parameters, `--parallel 1`, and speculative-decoding state.
- Seventeen unique Q11 fact texts and the item-level scoring protocol. The key
  remains measurement-only and must never enter prompt construction.
- Study 007's grounding-analysis procedure and Study 011 Amendment 001's
  five-replicate execution record as provenance, not assumed compatibility.

## Decisions that must be locked

| Decision | Why it is not silently inherited |
|---|---|
| Reader and runtime | The prior runtime produced a 3.0-point rubric switch; model or server changes break comparability |
| Exact prompt | Item use can change with instructions, provenance tags, answer format, or context ordering |
| Replicate schedule | Arm order and process lifetime can expose the server-slot divergence seen in Study 011 |
| Primary item-use definition | Correctness, delivery support, omission, contradiction, and invention are distinct outcomes |
| Primary paired statistic and bar | Five replicates do not by themselves define a pass, null, or noise bound |
| Rater/adjudication protocol | Mechanical matching can miss paraphrases; human or model raters can import rubric leakage and disagreement |
| Targeted reader arm | NF-006 proves targeted availability safety, not targeted answer safety; adoption and causal Q11 characterization require different scopes |
| Failure and signal dispositions | Both must be reachable and registered before generation; no post-result `carries signal` tier |

## Required preflight evidence

| Check | Required answer before registration can execute |
|---|---|
| PF1 | Every input exists, is readable, hash-bound, and counted |
| PF2 | Rendered C0/T1 prompt identity is demonstrated on real bytes; only the retrieval block differs |
| PF3 | Prompt seal precedes generation; answer seal precedes item scoring; scores precede arm unblinding |
| PF4 | Every bar and both branches are reachable on synthetic 17-bit vectors; no empty scored population |
| PF5 | Prompt, answer, and item identities use content hashes only |
| PF6 | C0/T1 payload digests and 12/17 versus 14/17 availability reproduce exactly |
| PF7 | Process and seed behavior are characterized across the intended five-replicate schedule |
| PF8 | State what 5x2 Q11 answers can and cannot resolve; it cannot estimate population-level reader effects |
| PF9 | Audit whether item-use scoring can pass through memorized unsupported facts, keyword echoes, or omitted delivered facts |
| PF10 | State whether the study is characterization only or an adoption gate; availability alone is not reused as the verdict |

## Minimum gate order for the eventual registration

1. Registration and input integrity.
2. Leakage and prompt-difference proof.
3. Frozen NF-006 payload and availability reproduction.
4. Reader/runtime and replicate-schedule characterization.
5. Prompt seal committed.
6. Five replicates per arm generated under the locked schedule.
7. Answers committed and completeness checked.
8. Blind 17-item fact-use vectors committed with rationales.
9. Arm mapping opened and registered paired rule applied once.
10. Mechanism logs opened only after outcome commitment.

This checklist is not a pre-registration, contains no outcome bar, and grants no
permission to implement or run NF-008.
