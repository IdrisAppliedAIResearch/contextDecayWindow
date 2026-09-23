"""AF-FT-003: V2 bundle decomposition — null-rows vs margin vs smoothing (plan 3f841945).

train N? [seeds]  N1 null rows only | N2 +margin .5 | N3 +LS .05; data fixed = V1H
eval              reused from af_ft002 (sample2, E17, McNemar vs R0, null quality)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import af_ft001 as F  # noqa: E402
import af_ft002 as F2  # noqa: E402

VARIANTS = {'N1': dict(margin=0.0, ls=0.0),
            'N2': dict(margin=F.MARGIN, ls=0.0),
            'N3': dict(margin=0.0, ls=F.LS)}


def main(tag, seeds=(20261011, 20261012, 20261013)):
    b = F2._build()
    rows = F._rows_for('V1H', b)  # frozen V1H data for every N variant
    for s in seeds:
        F2.train(tag, s, use_null=True, rows=rows, **VARIANTS[tag])


if __name__ == '__main__':
    if sys.argv[1] == 'eval':
        F2.evaluate(tags=('N1', 'N2', 'N3'), outpath=F2.ART / 'ft003' / 'results.json')
    else:
        seeds = tuple(int(x) for x in sys.argv[3].split(',')) if len(sys.argv) > 3 else (20261011, 20261012, 20261013)
        main(sys.argv[1], seeds)
