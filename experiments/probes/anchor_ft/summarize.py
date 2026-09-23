import json
r = json.load(open('experiments/probes/anchor_ft/artifacts/results.json', encoding='utf-8'))
s = r['summary']
for cfg in ('R0', 'V1', 'V1H', 'V2'):
    d = s[cfg]
    print(f"{cfg:4} exact {d['exact_mean']:5.2f}+-{d['exact_sd']:.2f}  "
          f"any {d['any_mean']:5.2f}+-{d['any_sd']:.2f}  "
          f"gated_any {d['gated_any_mean']:5.2f}  E17 {d['e17']}")
print()
for cfg, rows in s['mcnemar_any_vs_R0_sameseed'].items():
    print(f"{cfg:4} any-net vs R0 per seed {[x['net'] for x in rows]}  p {[x['p'] for x in rows]}")
n = s['null_head_V2_seed0']
print()
print('V2 null head: calib_auroc', n['calib_auroc'], 'heldout_auroc', n['heldout_auroc'],
      'cat5 mean_pnull', n['cat5_descriptive']['mean_pnull'])
print('coverage:', [(t['threshold'], t['anchor_coverage'], t['null_leak']) for t in n['coverage_table']])
