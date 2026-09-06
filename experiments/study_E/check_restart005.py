"""Exercise capture failure boundaries without model calls or study answers."""
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import runtime005 as rt
import restart_confirmation005 as runner

def main():
    checks=rt.fixtures()
    rows=[dict(physical_id=str(i),prompt_sha256=str(i),seed=5005,stage='fixture') for i in range(2)]
    store={'0':'first','1':'second'}
    with tempfile.TemporaryDirectory() as temp:
        root=Path(temp)
        for case in ['success','capped','timeout']:
            directory=root/case;directory.mkdir()
            def request(route,value):
                if case=='timeout' and value['id_slot']==0:raise TimeoutError('planted')
                return dict(content='office',stop_type='limit' if case=='capped' and value['id_slot']==0 else 'eos',truncated=False)
            with patch.object(rt,'request',request):
                if case=='success':assert len(rt.capture_wave(rows,store,directory,2))==2
                else:
                    try:rt.capture_wave(rows,store,directory,2)
                    except (AssertionError,RuntimeError):pass
                    else:raise AssertionError('Failure gate did not fire')
            captures=[json.loads(s) for s in (directory/'responses.jsonl').read_text().splitlines()]
            assert len(captures)==(1 if case=='timeout' else 2)
            assert len(list(directory.glob('pending_*.json')))==(1 if case=='timeout' else 0)
        # Runtime/input gate must reject before any inference request.
        with patch.object(runner,'O',root/'unsealed'),patch.object(runner.b,'prereqs'),patch.object(rt,'request') as request:
            try:runner.run()
            except Exception:pass
            else:raise AssertionError('Missing input lock accepted')
            request.assert_not_called()
    checks.update(capture_success=True,capped_wave_drained_and_persisted=True,
                  uncertain_journal_preserved=True,missing_input_blocks_inference=True)
    rt.save(rt.PROBE/'restart_preflight.json',checks)
    print(json.dumps(checks))

if __name__=='__main__':main()
