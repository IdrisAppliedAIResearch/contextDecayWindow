"""Run with the installed-wheel interpreter, isolated from repository imports."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np
import episodic
from episodic import EpisodeStore, EpisodicConfig


def embed(text):
    v = np.zeros(1024, dtype=np.float32)
    v[0 if 'relevant' in text or text == 'query' else 1] = 1
    return v


def child(path):
    with EpisodeStore(path, embedder=embed) as store:
        if not store._all_episodes():
            for i in range(40):
                store.append('user', 'relevant' if i == 0 else str(i))
                store.append('assistant', 'source')
        payload, report = store.context('query')
        assert report.episodes_delivered == 33 and report.recency_count == 32
        print(hashlib.sha256(payload.encode()).hexdigest())


def main():
    module = Path(episodic.__file__).resolve()
    assert 'site-packages' in str(module) and 'smoke-env' in str(module), module
    assert episodic.__version__ == '0.3.0'
    with tempfile.TemporaryDirectory() as directory:
        path = str(Path(directory)/'store.db')
        args = [sys.executable, '-I', str(Path(__file__).resolve()), 'child', path]
        first = subprocess.check_output(args, text=True).strip()
        second = subprocess.check_output(args, text=True).strip()
        assert first == second
        with EpisodeStore(path, EpisodicConfig(recency_window_n=0),
                          embedder=embed, override_config=True) as store:
            assert store.context('query')[1].episodes_delivered == 1
    out = Path(__file__).parent/'timeline_artifacts'
    wheel = out/'dist/episodic_chat-0.3.0-py3-none-any.whl'
    result = {'status': 'PASS', 'version': episodic.__version__,
        'module_path': str(module), 'python': sys.version, 'numpy': np.__version__,
        'wheel_sha256': hashlib.sha256(wheel.read_bytes()).hexdigest(),
        'cross_process_context_sha256': first,
        'default_continuity_and_opt_out': True, 'fresh_processes': 2,
        'model_calls': 0, 'embedder': 'fixed deterministic test vectors'}
    (out/'wheel_smoke.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    if len(sys.argv) > 1:
        child(sys.argv[2])
    else:
        main()
