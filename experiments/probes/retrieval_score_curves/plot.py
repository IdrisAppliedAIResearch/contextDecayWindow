"""Standalone figure from committed replay curves and descriptive annotations."""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

P=Path(__file__).resolve().parent
ROOT=P.parents[2]
curves=json.loads((P/'artifacts/curves.json').read_text())
targets=json.loads((P/'artifacts/target_diagnostic.json').read_text())
target_by_id={r['id']:r for r in targets}
es=[c for c in curves if c['study']=='E' and c['id'] in target_by_id]
ds=[c for c in curves if c['study']=='D' and c['type']=='T1']
miss=min((c for c in es if target_by_id[c['id']]['miss']),key=lambda c:c['id'])
complete=min((c for c in es if not target_by_id[c['id']]['miss']),key=lambda c:c['id'])
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
fig,axs=plt.subplots(2,2,figsize=(13,8.5),layout='constrained')
blue='#2563a6';red='#bd403b';green='#248567'
def envelope(ax,cs,metric,color,label):
    vals=np.array([sorted(c[metric],reverse=True) for c in cs]);x=np.arange(1,vals.shape[1]+1)
    ax.plot(x,np.median(vals,axis=0),color=color,label=label,lw=2)
    ax.fill_between(x,*np.quantile(vals,[.25,.75],axis=0),color=color,alpha=.16)
ax=axs[0,0];envelope(ax,es,'cc80',blue,'Study E before questions (128)')
ax.axvline(108.5,color=red,ls='--',lw=1.5)
ax.text(111,.5,'Unrelated\ncontinuity',color=red,fontsize=10)
ax.set(title='The largest drop finds the corpus seam',xlabel='Rank by combined relevance',ylabel='CC80 score (query-normalized)',ylim=(-.03,1.06));ax.legend(loc='lower left',frameon=False)
ax=axs[0,1];envelope(ax,es,'cosine',blue,'Study E before (128)');envelope(ax,ds,'cosine',green,'Study D before / T1 (32)')
ax.set(title='Raw cosine also decays, but its shape changes',xlabel='Rank by raw cosine',ylabel='Raw cosine similarity');ax.legend(frameon=False,fontsize=10)
ax=axs[1,0]
for c,color,label in [(miss,red,'Existing retrieval miss'),(complete,blue,'Existing complete evidence')]:
    vals=[c['cc80'][i] for i in c['order']];ax.plot(np.arange(1,109),vals[:108],color=color,lw=1.8,label=label)
    t=target_by_id[c['id']];r=t['target_rank'];ax.scatter([r],[vals[r-1]],color=color,s=70,zorder=5)
    ax.annotate(f'Needed update, rank {r}',(r,vals[r-1]),xytext=(r+3,vals[r-1]-.10),fontsize=9,color=color,arrowprops=dict(arrowstyle='-',color=color))
ax.set(title='Needed updates sit inside the high-score plateau',xlabel='Rank within the first 108 records',ylabel='CC80 score',ylim=(.35,1.04));ax.legend(loc='lower left',frameon=False,fontsize=9)
ax=axs[1,1];order=miss['temporal_order'][:20];vals=[miss['cc80'][i] for i in order];x=np.arange(1,len(order)+1)
ax.plot(x,vals,color=red,marker='.',lw=1.5)
t=target_by_id[miss['id']];target_i=miss['order'][t['target_rank']-1];r=miss['temporal_order'].index(target_i)+1
ax.scatter([r],[miss['cc80'][target_i]],color=green,s=90,zorder=5,label='Needed update')
ax.axvline(10.5,color='#555555',ls='--',label='Existing temporal pack ends')
ax.set(title='Newest-first temporal order is not score order',xlabel='Temporal candidate position (anchor first)',ylabel='CC80 score',xticks=[1,5,10,15,20],ylim=(.35,1.04));ax.legend(loc='lower right',frameon=False,fontsize=9)
fig.suptitle('Existing retrieval curves: useful structure, no demonstrated completion threshold',fontsize=15,fontweight='bold')
fig.supxlabel('Exploratory replay · No model calls · Shading: middle 50% across questions · Example selection: lowest stable ID in each stratum',fontsize=9)
fig.savefig(P/'score_curves.png',dpi=160)
fig.savefig(P/'score_curves.pdf')
(P/'artifacts/figure_manifest.json').write_text(json.dumps(dict(miss_id=miss['id'],miss_history=miss['history'],complete_id=complete['id'],complete_history=complete['history'],shading='25th to75th percentile',selection='Lowest stable query identity within existing complete/miss strata'),indent=2)+'\n')
