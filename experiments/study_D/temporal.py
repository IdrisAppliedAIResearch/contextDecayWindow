"""Label-free restricted grammar and frozen-packer temporal allocation."""
import re
from episodic._chat_context import build_chat_context
from episodic._config import EpisodicConfig
from episodic._context import _recency_window
from episodic._packing import pack_stm_payload
from episodic._ranking import rank_cc80
from episodic._render import render_stm_payload

CONFIG=EpisodicConfig()
BUDGET=32000
TEMPORAL_BUDGET=8000

def temporal_order(episodes,query,ranking):
    names=re.findall(r'"([^"\n]+)"',query)
    def carriers(name):
        return [i for i,e in enumerate(episodes) if f'"{name}"' in e['user_message']]
    if len(re.findall(r'\b(before|after)\b',query,re.I))>1:
        return [],{'reason':'ambiguous_temporal_clauses'}
    if len(names)==2 and re.search(r'\b(before|after)\b',query,re.I):
        subject,anchor=names
        if not carriers(subject):
            return [],{'reason':'missing_subject'}
        anchors=[i for i in carriers(anchor) if re.search(r'\b(meeting|event)\b',episodes[i]['user_message'],re.I)]
        if len(anchors)!=1:
            return [],{'reason':'ambiguous_or_missing_anchor','anchors':anchors}
        a=anchors[0]
        before=bool(re.search(r'\bbefore\b',query,re.I))
        eligible=set(i for i in carriers(subject) if (episodes[i]['turn_number']<episodes[a]['turn_number'] if before else episodes[i]['turn_number']>episodes[a]['turn_number']))
        order=[i for i in ranking.order if i in eligible]
        return [a]+order,{'reason':'anchored','anchors':anchors,'eligible':sorted(eligible)}
    if len(names)==1 and re.search(r'\b(latest|current)\b',query,re.I):
        candidates=carriers(names[0])
        return sorted(candidates,key=lambda i:(-episodes[i]['turn_number'],episodes[i]['id'])),{'reason':'recency','eligible':candidates}
    if len(names)==2 and re.fullmatch(r'How many days elapsed between "[^"\n]+" and "[^"\n]+"\?',query):
        matches=[carriers(name) for name in names]
        if all(len(x)==1 for x in matches):
            return [matches[0][0],matches[1][0]],{'reason':'duration','anchors':[x[0] for x in matches]}
        return [],{'reason':'ambiguous_or_missing_anchor'}
    return [],{'reason':'unsupported'}

def build(episodes,query,vector):
    baseline,report=build_chat_context(episodes=episodes,query_text=query,query_embedding=vector,budget=BUDGET,config=CONFIG)
    ranking=rank_cc80(episodes,query,vector,dense_weight=.8,bm25_k1=1.2,bm25_b=.75)
    order,trace=temporal_order(episodes,query,ranking)
    recent=list(_recency_window(episodes,32))
    recent_ids={e['id'] for e in recent}
    eligible=[i for i in order if episodes[i]['id'] not in recent_ids]
    if not eligible:
        return baseline,baseline,{'route':trace,'fallback':True,'ranking':list(ranking.order),'baseline_report':report.__dict__}
    temporal=pack_stm_payload([], [episodes[i] for i in eligible],TEMPORAL_BUDGET)
    first=list(temporal.selected_ids)
    merged=first+[episodes[i]['id'] for i in ranking.order if episodes[i]['id'] not in set(first)|recent_ids]
    by_id={e['id']:e for e in episodes}
    packed=pack_stm_payload([],[by_id[x] for x in merged],BUDGET)
    treatment=render_stm_payload(recent,[by_id[x] for x in packed.selected_ids])
    return baseline,treatment,{'route':trace,'fallback':False,'ranking':list(ranking.order),'temporal_ids':first,'selected_ids':list(packed.selected_ids),'baseline_report':report.__dict__}
