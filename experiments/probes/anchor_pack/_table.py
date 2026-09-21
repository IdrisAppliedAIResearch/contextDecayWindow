import json
from math import comb

d = json.load(open('experiments/probes/anchor_pack/artifacts/results.json', encoding='utf-8'))['summary']


def mc(n10, n01):
    n = n10 + n01
    if not n:
        return None
    k = min(n10, n01)
    return round(min(1.0, sum(comb(n, i) for i in range(0, k + 1)) * 2 / 2 ** n), 4)


print('control', d['positive_control'])
print()
for b in ('500', '1000', '2000', '4000', '8000'):
    print('== budget', b)
    for a, v in d['budgets'][b]['arms'].items():
        print(f"  {a:16s} any120={v['any_ev_120']:3d} all120={v['all_ev_120']:3d} "
              f"ans={v['ans_ok']:3d} chars_med={v['median_chars']} feasible={v['feasible']}")
    for a, v in d['budgets'][b]['matched_vs_bm25'].items():
        print(f"  vsBM25 {a:11s} n={v['n']} all {v['gains_all']}/{v['losses_all']} "
              f"p={mc(v['gains_all'], v['losses_all'])} "
              f"any {v['gains_any']}/{v['losses_any']} p={mc(v['gains_any'], v['losses_any'])}")
print()
print('disposition', d['disposition_anchor_w2_vs_bm25'], 'delta', d['delta_all_ev_by_budget'])
print('crossover any70', d['crossover_budget_any_ev_70'])
print()
for b in ('500', '1000', '2000', '8000'):
    print('hit/miss', b, {k: (v['all_ev_hit'], v['n_hit'], v['all_ev_miss'], v['n_miss'])
                          for k, v in d['hit_miss_split_by_budget'][b].items()})
