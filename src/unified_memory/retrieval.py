"""Finite fixed-cue agenda and explicit candidate ledger. No model dependency."""
from __future__ import annotations
from dataclasses import dataclass
import heapq
import numpy as np
from .control import cosine_matrix


@dataclass(frozen=True)
class Policy:
    contextual: float
    support: float
    reference: float
    path_floor: float = .48

    def __post_init__(self):
        if any(not np.isfinite(v) or not -1 <= v <= 1 for v in (self.contextual, self.support, self.reference)) or not 0 <= self.path_floor <= 1:
            raise ValueError("Invalid route threshold")


@dataclass(frozen=True)
class Conflict:
    reference_id: str
    candidate_id: str
    source_ids: tuple[str, ...]
    rule: str


def retrieve(units, direct_vectors, contextual_vectors, contexts, references, cue_vectors,
             query_vector, policy: Policy, *, conflicts=(), static_scores=None):
    units = tuple(sorted(units, key=lambda u: (u.position, u.id)))
    ids = [u.id for u in units]
    if len(set(ids)) != len(ids) or len({u.conversation for u in units}) > 1:
        raise ValueError("Duplicate identities or cross-conversation query domain")
    if not units:
        return dict(selected=[], direct=[], contextual=[], bindings=[], admissions={},
                    operations=0, stop="FRONTIER_EXHAUSTED", unresolved_support=[])
    universe = set(ids)
    by_id = {u.id: u for u in units}
    if any(set(contexts[key]) - universe for key in ids):
        raise ValueError("Contextual view contains sources outside the knowledge horizon")
    dm = cosine_matrix([direct_vectors[key] for key in ids])
    cm = cosine_matrix([contextual_vectors[key] for key in ids])
    q = np.array(query_vector, dtype=np.float64, copy=True)
    if not np.isfinite(q).all() or not np.linalg.norm(q):
        raise ValueError("Invalid query vector")
    q /= np.linalg.norm(q)
    ds, cs = dm @ q, cm @ q
    direct = {key for key, score in zip(ids, ds) if score >= .48}
    contextual = {key for key, score in zip(ids, cs) if score >= policy.contextual}
    refs = {r.id: r for r in references}
    if len(refs) != len(references) or any(r.unit_id not in universe for r in references):
        raise ValueError("Invalid reference domain")
    by_unit = {key: [] for key in ids}
    for ref in references:
        if not by_id[ref.unit_id].text[ref.offset:].startswith(ref.text):
            raise ValueError("Reference cue is not an exact source span")
        by_unit[ref.unit_id].append(ref)
    forbidden = {}
    for conflict in conflicts:
        if (conflict.reference_id not in refs or conflict.candidate_id not in universe
                or not conflict.source_ids or set(conflict.source_ids) - universe or not conflict.rule):
            raise ValueError("Conflict lacks eligible source provenance")
        forbidden[(conflict.reference_id, conflict.candidate_id)] = conflict
    if static_scores is not None:
        if static_scores["ids"] != ids or set(static_scores["references"]) != set(refs):
            raise ValueError("Static score domain differs")
    selected, admissions, queue, finalized, activation = set(), {}, [], set(), {}
    bindings, unresolved = [], []
    suppressed = 0

    def admit(key, reason, strength):
        admissions.setdefault(key, set()).add(reason)
        selected.add(key)
        if strength > activation.get(key, -1):
            if key in finalized:
                raise AssertionError("Finalized activation improved")
            activation[key] = strength
            heapq.heappush(queue, (-strength, key))

    for key in sorted(direct):
        admit(key, "direct", float(ds[ids.index(key)]))
    for key in sorted(contextual):
        admit(key, "contextual", float(cs[ids.index(key)]))
    operations = 0
    while queue:
        negative, key = heapq.heappop(queue)
        if key in finalized or -negative < activation[key]:
            continue
        finalized.add(key)
        parent_activation = activation[key]
        operations += 1
        if key in contextual:
            operations += 1
            index = ids.index(key)
            scores = dm @ dm[index] if static_scores is None else static_scores["support"][index]
            additional = []
            for candidate, score in zip(ids, scores):
                if candidate not in contexts[key] or set(by_id[candidate].member_ids).intersection(by_id[key].member_ids):
                    continue
                if score >= policy.support:
                    strength = parent_activation * max(0., min(1., float(score)))
                    if strength < policy.path_floor:
                        suppressed += 1
                        continue
                    additional.append(candidate)
                    admit(candidate, "context-support:" + key, strength)
            if not additional:
                unresolved.append(key)
        for ref in by_unit[key]:
            operations += 1
            cue = np.asarray(cue_vectors[ref.id], dtype=np.float64)
            if not np.isfinite(cue).all() or not np.linalg.norm(cue):
                raise ValueError("Invalid reference cue vector")
            scores = dm @ (cue / np.linalg.norm(cue)) if static_scores is None else static_scores["references"][ref.id]
            for candidate, score in zip(ids, scores):
                if set(by_id[candidate].member_ids).intersection(by_id[ref.unit_id].member_ids):
                    continue
                if score < policy.reference:
                    continue
                strength = parent_activation * max(0., min(1., float(score)))
                if strength < policy.path_floor:
                    suppressed += 1
                    continue
                conflict = forbidden.get((ref.id, candidate))
                bindings.append(dict(reference=ref.id, source=ref.unit_id, candidate=candidate,
                                     score=float(score), status="rejected-under-rule" if conflict else "unresolved",
                                     activation=strength,
                                     relation="candidate-antecedent" if by_id[candidate].position < by_id[ref.unit_id].position else "candidate-corroboration",
                                     conflict_rule=conflict.rule if conflict else None))
                if conflict is None:
                    admit(candidate, "reference:" + ref.id, strength)
            # Every reference search has one immutable cue and finite domain.
    bound = len(units) + len(references) + len(contextual)
    if operations > bound or not direct.issubset(selected):
        raise AssertionError("Finite agenda or direct retention violated")
    return dict(selected=[key for key in ids if key in selected],
                direct=[key for key in ids if key in direct],
                contextual=[key for key in ids if key in contextual],
                bindings=bindings, admissions={key: sorted(value) for key, value in sorted(admissions.items())},
                activation={key:float(value) for key, value in sorted(activation.items())},
                weak_paths_suppressed=suppressed,
                operations=operations, operation_bound=bound, stop="FRONTIER_EXHAUSTED",
                unresolved_support=sorted(unresolved))
