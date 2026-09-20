"""Losslessly archive completed raw responses; retain and verify raw bytes."""
import gzip
import hashlib
import json
from pathlib import Path

OUT=Path(__file__).parent/'artifacts/confirmation'

def main():
    gate=json.loads((OUT/'reader_gate.json').read_text())
    raw=(OUT/'responses.jsonl').read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    if gate['status']=='PASS':
        assert sha==gate['responses_sha256']
    archive=gzip.compress(raw,compresslevel=9,mtime=0)
    assert gzip.decompress(archive)==raw
    path=OUT/'responses.jsonl.gz'
    assert not path.exists()
    path.write_bytes(archive)
    (OUT/'response_archive.json').write_text(json.dumps({'raw_bytes':len(raw),'raw_sha256':sha,'archive_bytes':len(archive),'archive_sha256':hashlib.sha256(archive).hexdigest(),'encoding':'gzip, original JSONL bytes preserved','raw_local_file_retained':True},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'raw_bytes':len(raw),'archive_bytes':len(archive)}))

if __name__=='__main__':
    main()
