import sys, json, glob, os
sys.path.insert(0, 'experiments/probes/anchor_reader')
sys.path.insert(0, 'src')
import af_read001 as R
import af_read002 as T
from analysis.hh001_prompt import render_reader_prompt

OUT = R.HERE / 'artifacts/af_read002'
ctx = R.load(OUT / 'contexts.json')
items = {i['qid']: i for i in ctx['items']}
natives = R.load(OUT / 'natives.json') if (OUT / 'natives.json').exists() else {}
bad = []
n = 0
for arm, blk, shk, nk in (('B_ANCHOR8K', 'block_b', 'b_sha', 'b_native'),
                          ('C_ANCHOR8K_CC80', 'block_c', 'c_sha', 'c_native')):
    for f in glob.glob(str(OUT / f'reader/{arm}__*.json')):
        rec = json.load(open(f, encoding='utf-8'))
        qid = rec['qid']
        it = items[qid]
        n += 1
        if R.sha_text(render_reader_prompt(T._Q(qid), it[blk])) != it[shk]:
            bad.append((arm, qid, 'ctx-sha'))
        key = qid + '|' + nk
        if key in natives and R.sha_text(natives[key]) != rec['prompt_sha256']:
            bad.append((arm, qid, 'native-sha'))
print('checked', n, 'reader files; mismatches:', len(bad), bad[:5])
