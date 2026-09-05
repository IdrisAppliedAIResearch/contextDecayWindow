"""Bounded Part 1 inventory and frozen baseline replay; never scores answers."""
import concurrent.futures
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
CONTROL = ROOT.parent / 'contextDecayWindow-study-D-control'
OUT = ROOT / 'experiments/study_D/artifacts/part1'

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def write(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8')

def main():
    assert subprocess.check_output(['git', 'status', '--porcelain'], cwd=CONTROL).strip() == b''
    sys.path[:0] = [str(CONTROL / 'episodic/src'), str(CONTROL / 'src')]
    import numpy as np
    import episodic._chat_context as chat
    from episodic._config import EpisodicConfig
    from analysis.tc001_exploration import CACHE_PATH, VECTOR_MANIFEST
    spec = importlib.util.spec_from_file_location('frozen_port', CONTROL / 'scripts/verify_cc007_port.py')
    parity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parity)
    parity.OUTPUT = OUT / 'parity.json'
    paths = [CACHE_PATH, VECTOR_MANIFEST, parity.BLIND, parity.CC80_FROZEN, parity.ASPECT_FROZEN,
             Path(chat.__file__), CONTROL / 'scripts/verify_cc007_port.py']
    paths += list((CONTROL / 'episodic/src/episodic').glob('*.py'))
    paths = sorted(set(paths))
    inventory = [{'path': str(p), 'present': p.is_file(), 'bytes': p.stat().st_size if p.is_file() else None} for p in paths]
    if not all(row['present'] for row in inventory):
        write('inventory.json', {'status':'MISSING_INPUT', 'files':inventory})
        raise RuntimeError('PF1 missing input')
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 1)) as pool:
        for row, sha in zip(inventory, pool.map(digest, paths)):
            row['sha256'] = sha
    write('inventory.json', {'status':'PASS', 'files':inventory, 'control_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=CONTROL,text=True).strip(), 'python':sys.executable})
    started = time.monotonic()
    result = parity.verify()
    print(json.dumps({'parity':result['status'], 'seconds':time.monotonic()-started}), flush=True)
    rng = np.random.default_rng(5005)
    q = rng.normal(size=1024).astype(np.float32)
    rows = []
    for count in (0, 1, 32, 35, 120, 1000):
        episodes = [{'id':f'fixture-{i}', 'turn_number':i, 'user_message':f'Source {i}. '+('Trace material. '*80), 'assistant_message':'Recorded.', 'embedding':rng.normal(size=1024).astype(np.float32)} for i in range(1,count+1)]
        payload, report = chat.build_chat_context(episodes=episodes,query_text='Trace material',query_embedding=q,budget=32000,config=EpisodicConfig())
        again, _ = chat.build_chat_context(episodes=episodes,query_text='Trace material',query_embedding=q,budget=32000,config=EpisodicConfig())
        assert payload == again
        expected = tuple(f'fixture-{i}' for i in range(max(1,count-31),count+1))
        assert set(report.recent_ids) == set(expected)
        rows.append({'count':count,'total_chars':len(payload),'retrieval_chars':report.retrieval_chars_delivered,'recent_count':report.recency_count,'recent_ids':report.recent_ids,'payload_sha256':hashlib.sha256(payload.encode()).hexdigest(),'repeated_identical':payload==again})
    write('public_behavior.json', {'status':'PASS','module':chat.__file__,'fixtures':rows,'scope':'Synthetic behavior checks plus real frozen parity; no reader or temporal route tested.'})
    assert subprocess.check_output(['git','status','--porcelain'],cwd=CONTROL).strip() == b''
    print(json.dumps({'public_behavior':'PASS','fixtures':len(rows)}),flush=True)

if __name__ == '__main__':
    main()
