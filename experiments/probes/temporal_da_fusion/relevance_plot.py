"""Static scientific diagnostic of the fixed cosine boundary and timeline."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from preflight import ROOT,P,I,read,sha

out=P/'relevance_artifacts'
curves=read(ROOT/'experiments/probes/retrieval_score_curves/artifacts/curves.json')
primary=[r for r in curves if r['study']=='E' and r['type'] in ['straight','irrelevant','future','proposal']]
scores=np.array([sorted(r['cosine'],reverse=True) for r in primary]);x=np.arange(1,141)
example=next(r for r in primary if 'Harbor-485' in r['query'])
label=read(I/'labels.json')[example['id']];required=set(label['gold_ids'])
fig,axs=plt.subplots(1,2,figsize=(12,4.6),layout='constrained')
ax=axs[0];ax.fill_between(x,np.quantile(scores,.25,axis=0),np.quantile(scores,.75,axis=0),color='#a9c4e8',alpha=.65,label='Middle 50% of 128 queries')
ax.plot(x,np.median(scores,axis=0),color='#23558a',lw=2,label='Median cosine')
ax.axhline(.48,color='#a33b30',ls='--',label='Fixed threshold 0.48')
ax.set(title='Similarity-sorted retrieval curve',xlabel='Rank by raw cosine',ylabel='Raw cosine similarity',xlim=(1,140));ax.legend(fontsize=8,loc='lower left')
ax=axs[1];s=np.array(example['cosine']);turns=np.array(example['turns']);keep=s>=.48
ax.scatter(turns[~keep],s[~keep],s=18,color='#aeb5bd',label='Below threshold')
ax.scatter(turns[keep],s[keep],s=19,color='#248566',label='Passes 0.48')
idx=[i for i,k in enumerate(example['ids']) if k in required]
ax.scatter(turns[idx],s[idx],s=150,marker='*',color='#d57920',edgecolor='black',linewidth=.5,label='Required update / anchor',zorder=4)
ax.axhline(.48,color='#a33b30',ls='--');ax.set(title='Same scores in source order: Harbor-485',xlabel='Source turn (chronological)',ylabel='Raw cosine similarity',xlim=(0,141));ax.legend(fontsize=8,loc='lower left')
for ax in axs:ax.grid(alpha=.18);ax.spines[['top','right']].set_visible(False)
fig.suptitle('Relevance selects the records; chronology orders their presentation',fontsize=13)
fig.savefig(out/'relevance_curve.png',dpi=160);plt.close(fig)
(out/'figure_manifest.json').write_text(json.dumps(dict(curves_sha256=sha(ROOT/'experiments/probes/retrieval_score_curves/artifacts/curves.json'),script_sha256=sha(P/'relevance_plot.py'),example_id=example['id'],selection='Previously audited Harbor-485 miss; no new visual outcome selection',image_sha256=sha(out/'relevance_curve.png')),indent=2)+'\n',encoding='utf-8')
