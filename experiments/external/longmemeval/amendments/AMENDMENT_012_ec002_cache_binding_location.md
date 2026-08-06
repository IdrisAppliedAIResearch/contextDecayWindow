# EC-002 Amendment 002 — A0 cache binding location

**Study:** EC-002 K-first packing diagnostic
**Registration anchor:** `8c75d7e22258c56cb6b422c0dfcc013cddd65613`
**Amendment 001 anchor:** `2a675eefcf2fc53fb0d54894f7134e05dabcbdf4`
**Status:** AUTHORIZED AFTER A1 PREFLIGHT BLOCKED AND BEFORE A1
**Authorization:** Program author authorized blocker amendments and instructed
that A1 proceed after the cache contract, August 5, 2026.

## Trigger and evidence

The amended A0 reproduction passed and was committed at
`d9fd44453509412fd7c3571f6a793f7a63945e22`. A1 preflight stopped before
creating an output directory because `a0_reproduction_gate.json` did not
contain its `embedding_cache` object.

The amended-A0 reuse branch recorded the cache in the sibling
`source_integrity.json` but failed to copy it into the gate JSON. Both files:

- were produced by the same run;
- have status `PASS`;
- are committed together at `d9fd4445`;
- carry registration
  `8c75d7e22258c56cb6b422c0dfcc013cddd65613`; and
- sit in the same immutable run directory.

The source-integrity record binds:

- path:
  `experiments/external/longmemeval/runs/ec002_k_first/ec002_exact_solo_embeddings.db`;
- bytes: 1,050,013,696;
- entries: 96,585;
- file SHA-256:
  `e8a31513700a0a5d1cfe34b4703bbe3c8c85dc3ca29188d7cc480c2e2417a7ad`;
- model SHA-256:
  `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`;
- call shape: solo; and
- amended-A0 misses: 0.

CC-006 independently adopted the same retained file and added canonical
content SHA-256
`d60d723dea787b0d5bbd25a3c89f2a1c20b92a2a79813f34688a12e7c346a180`.

No A1 output was created or read.

## Change

When a passing A0 gate lacks an inline `embedding_cache` object, A1 preflight
may load it from the sibling `source_integrity.json` only if all of these
mechanical checks pass:

1. the gate and source-integrity files are both tracked, clean, and committed
   in the same commit;
2. both records have status `PASS`;
3. both record the EC-002 registration SHA;
4. source integrity records mode `reproduce`;
5. its script-before and script-after hashes are identical;
6. its cache has 96,585 entries, zero misses, solo call shape, and the exact
   path, file SHA, and model SHA above; and
7. the committed CC-006 adoption record matches that path, file SHA, model
   SHA, entry count, and canonical content SHA.

Failure of any check stops A1. The loader records that the cache binding came
from source integrity rather than the gate JSON.

## Rationale

This changes only which committed file supplies already-recorded provenance.
It does not infer a missing value, edit a run artifact, weaken a retrieval
criterion, or permit a different cache. Re-running A0 solely to duplicate the
same cache object into a second JSON file would add no measurement.

## Exclusions

- No locked EC-001 or committed EC-002 artifact is edited.
- No A0 outcome, rank tolerance, coverage cap, or integrity criterion changes.
- No different cache path, vector, model, or call shape is allowed.
- No A1 output is authorized unless every mechanical cross-check passes.
