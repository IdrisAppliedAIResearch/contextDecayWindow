# TC-015 — opportunity then utility: Part 1 exploration

**Type:** label-blind mechanism exploration  
**Status:** `STOPPED_AT_PART_1; INERT_SELECTION`  
**Date:** 2026-08-26

## Proposed mechanism

Keep the exact children retained by TC-014's opportunity admission, then emit
those children by descending frozen TC-013 edge utility before applying the
unchanged 50/50 protected allocator. Equal utilities preserve original parent
order and then content identity. No child is added, removed, reassigned or
rescored.

## Behavioral identity

TC-014 opportunity admission fixes the child set in parent order; the proposed
TC-015 mechanism changes only that retained set's emission order to descending
frozen edge utility.

The frozen TC-014 opportunity allocation was reproduced by identity and
payload digest on all 1,742 question-budget cells. The proposed order preserved
the opportunity set on all 1,742 cells.

## Distribution and absorbing states

| Measure | 16k | 32k |
|---|---:|---:|
| Retained children, min / median / max | 5 / 17 / 27 | 20 / 36 / 50 |
| Admitted children, min / median / max | 5 / 17 / 27 | 20 / 36 / 50 |
| Rows whose order changed | 868 / 871 | 871 / 871 |
| Rows whose payload digest changed | 868 / 871 | 871 / 871 |
| Selected identity sets changed vs opportunity | **0 / 871** | **0 / 871** |
| Selected identity sets changed vs TC-014 utility-pack | 871 / 871 | 871 / 871 |

No row retained zero or one child, and no row admitted zero retained children.
The absorbing state is instead capacity slack: opportunity admission always
leaves a retained list that fits in its protected half. Reordering therefore
changes serialization order but cannot change which evidence identities enter
the context.

## PF4 stop

An evidence-availability gain or loss versus TC-014 opportunity is unreachable:
the selected identity sets are identical on every planned comparison cell.
Registering complete-evidence bars after this finding would certify a treatment
that cannot affect the endpoint. TC-015 therefore stops before pre-registration,
selection freeze, label opening or outcome measurement.

This does not show that utility is generally useless. TC-014 utility-first
packing changed identities when it operated on the larger, unfiltered fan-out
list. It shows that the exact sequential opportunity filter and utility-first
packing cannot compose through this allocator because the filter removes the
packing contest.

## Integrity boundary

- TC-014 selection anchor:
  `32b1db4d5476cfe97eb6cb306c29c63d597b8bfc219ca73db181396ed5d750f7`.
- CC80 source anchor:
  `17e88abdc88547ec8abd96fb09ce8ae8e3f04c605d0081eed5f8cf837e2ad202`.
- Blind manifest anchor:
  `83bcadb1e029e14514841b65bd903904fe53420a246bc0a59cad99afaa0671b3`.
- Label artifacts were not opened by the mechanism exploration.
- Zero cache, embedding, LLM or generative calls.
- Scope is deterministic LoCoMo development selection behavior only.
