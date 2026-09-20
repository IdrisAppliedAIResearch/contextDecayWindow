"""Preliminary DA temporal-link adaptation; no outcome input or persistent state."""
from __future__ import annotations
import ast
import hashlib
import importlib.util
from pathlib import Path
import re
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
CONTROL = ROOT.parent / 'contextDecayWindow-fusion-E-control'
DA_ROOT = Path('C:/Users/muzaf/wt91')
DA_SOURCE = DA_ROOT / 'src/analysis/da001_linked_context.py'
DA_SHA = '5d77a3ee642f6becd7628dcc78bad158d57cc58478439a11f55f1116ba0748be'

spec = importlib.util.spec_from_file_location('frozen_e', CONTROL / 'experiments/study_E/mechanism.py')
E = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E)


def load_traversal():
    assert hashlib.sha256(DA_SOURCE.read_bytes()).hexdigest() == DA_SHA
    tree = ast.parse(DA_SOURCE.read_text(encoding='utf-8'))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'linked_order')
    # Execute the original function alone, without importing DA's corpus loaders.
    module = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), function], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = {'DA001Error': ValueError}
    exec(compile(module, str(DA_SOURCE), 'exec'), namespace)
    return namespace['linked_order']


linked_order = load_traversal()


def fuse(episodes, query, trace, baseline, *, links=True):
    """Consume only the frozen selector trace, source text and query."""
    active = not trace.get('unchanged') and bool(re.search(r'\bbefore\b', query, re.I))
    active = active and trace['route'].get('reason') == 'anchored'
    old = trace if not trace.get('unchanged') else trace['prior']
    if not active:
        return baseline, dict(selected_ids=old['selected_ids'], active=False, links=[])
    ranking = tuple(trace['prior']['ranking'])
    nodes = [SimpleNamespace(session_identity='source_history', pair_order=e['turn_number']) for e in episodes]
    order, linked = linked_order(nodes, ranking, 'TEMPORAL', len(ranking) if links else 0)
    recent = list(E._recency_window(episodes, 32))
    recent_ids = {e['id'] for e in recent}
    protected = list(trace['temporal_ids'])
    ids = list(dict.fromkeys(protected + [episodes[i]['id'] for i in order if episodes[i]['id'] not in recent_ids]))
    by = {e['id']: e for e in episodes}
    packed = E.pack_stm_payload([], [by[k] for k in ids], 32000)
    selected = list(packed.selected_ids)
    assert selected[:len(protected)] == protected
    # Capture the first-emission parent; a later original seed is not recursive expansion.
    seen, edges = set(), []
    chronological = sorted(range(len(episodes)), key=lambda i: episodes[i]['turn_number'])
    positions = {i: p for p, i in enumerate(chronological)}
    for seed in ranking if links else []:
        seen.add(seed)
        for p in (positions[seed]-1, positions[seed]+1):
            if 0 <= p < len(chronological):
                child = chronological[p]
                if child not in seen:
                    edges.append(dict(seed=episodes[seed]['id'], child=episodes[child]['id']))
                    seen.add(child)
    assert {edge['child'] for edge in edges} == {episodes[i]['id'] for i in linked}
    return E.render_stm_payload(recent, [by[k] for k in selected]), dict(
        selected_ids=selected, active=True, protected_ids=protected,
        order_ids=[episodes[i]['id'] for i in order], links=edges,
        linked_selected_ids=[episodes[i]['id'] for i in linked if episodes[i]['id'] in selected and episodes[i]['id'] not in protected],
        retrieval_chars=packed.serialized_chars)
