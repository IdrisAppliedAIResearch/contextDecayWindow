"""Six development calls only, as specified in extension 006."""
import json
from pathlib import Path
from reader_ablation import post

ROOT=Path(__file__).resolve().parent/'artifacts/part1'
OUT=ROOT/'cache_probe'

def main():
    assert json.loads((ROOT/'reader_ablation/gate.json').read_text())['status']=='PASS'
    OUT.mkdir(exist_ok=True)
    assert not (OUT/'responses.jsonl').exists()
    cells=json.loads((ROOT/'reader_ablation/prompt_seal.json').read_text())[:35]
    selected=[max(cells,key=lambda x:x['tokens']),min(cells,key=lambda x:x['tokens']),cells[0]]
    pairs=[]
    complete=True
    for i,cell in enumerate(selected):
        texts=[]
        for cache in (False,True):
            result=post('/completion',{'prompt':cell['prompt'],'seed':5005,'temperature':.6,'top_p':.95,'top_k':20,'min_p':0.,'repeat_penalty':1.,'presence_penalty':0.,'cache_prompt':cache,'n_predict':8192,'stream':False,'reasoning_format':'none'})
            with (OUT/'responses.jsonl').open('a',encoding='utf-8') as stream:
                stream.write(json.dumps({'pair':i,'cache':cache,'prompt_sha256':cell['sha256'],'response':result},sort_keys=True)+'\n')
                stream.flush()
            text=result.get('content','')
            complete &= bool(text.strip()) and result.get('stop_type')=='eos' and result.get('tokens_predicted',8192)<8192 and not result.get('truncated',False) and '<think>' not in text
            texts.append(text)
        pairs.append(texts[0]==texts[1])
    gate={'status':'PASS' if complete and all(pairs) else 'CACHE_DISALLOWED','paired_byte_identity':pairs,'complete':complete,'calls':6,'scores_opened':False}
    (OUT/'gate.json').write_text(json.dumps(gate,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(gate))

if __name__=='__main__':
    main()
