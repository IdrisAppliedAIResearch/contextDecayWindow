"""Parse CoNLL-2012 v12 (.gold_conll) English docs and extract coreference clusters.

v12 column layout (16 cols, some docs 12): 0 doc,1 sent,2 tok,3 word,4 pos,5 parse,
9 NER, 10 sense/num, 11 = COREFERENCE (numeric chain ids), 12-15 SRL.

Coreference uses matched (id / id) / ) brackets, interleaved with SRL brackets in the
SAME column. We separate them with a single stack, distinguishing an open by the char
after '(' (digit => coref, else SRL). This is the known-tricky v12 split; we VALIDATE
against a document whose clusters we can eyeball before trusting anything.
"""
import zipfile, re, os, collections

COREF_OPEN = re.compile(r"\((\d+)")


def parse_gold_conll(lines):
    """Return list of documents; each = dict(sents=[[word,...]], clusters={id:[(si,s,ti,e)]}).

    Cluster members stored as (sent_idx, start_tok, end_tok_exclusive); a chain id seen
    in multiple places links them into one entity.
    """
    # split into sentence rows
    sents = []
    cur_words, cur_coref = [], []
    def flush():
        if cur_words:
            sents.append((list(cur_words), list(cur_coref)))
        cur_words.clear(); cur_coref.clear()
    for l in lines:
        if not l.strip() or l.startswith("#"):
            flush(); continue
        c = l.split()
        if len(c) < 12:
            continue
        cur_words.append(c[3]); cur_coref.append(c[11])
    flush()

    # stack-based coref extraction over the whole doc token stream
    clusters = collections.defaultdict(list)  # chain_id -> list of (si,ti) mention-token hits
    stack = []  # entries: ('C', chain_id) or ('S',)
    open_spans = {}  # chain_id -> [si,ti] current open start
    for si, (words, corefs) in enumerate(sents):
        for ti, cf in enumerate(corefs):
            i = 0
            while i < len(cf):
                ch = cf[i]
                if ch == '(':
                    if i + 1 < len(cf) and cf[i+1].isdigit():
                        m = COREF_OPEN.match(cf, i)
                        cid = m.group(1)
                        stack.append(('C', cid))
                        open_spans.setdefault(cid, [si, ti])
                        i = m.end()
                        # trailing ')' immediately after digits may close it: "(50)" -> after "(50",
                        # the next char is ')' handled on next loop iteration
                        continue
                    else:
                        stack.append(('S',)); i += 1; continue
                elif ch == ')':
                    if stack:
                        typ = stack.pop()
                        if typ[0] == 'C':
                            cid = typ[1]
                            st, sti = open_spans.pop(cid, (si, ti))
                            clusters[cid].append((st, sti, si, ti))  # (startSi,startTi,endSi,endTi)
                    i += 1; continue
                else:
                    i += 1; continue
    return sents, dict(clusters)


def render(sents, member):
    ssi, sti, esi, eti = member
    toks = []
    si, ti = ssi, sti
    while True:
        toks.append(sents[si][0][ti])
        if (si, ti) == (esi, eti): break
        ti += 1
        if ti >= len(sents[si][0]): si += 1; ti = 0
    return " ".join(toks)


if __name__ == "__main__":
    zp = r"C:\Users\muzaf\AppData\Local\Temp\opencode\conll-2012.zip"
    z = zipfile.ZipFile(zp)
    n = "conll-2012/v12/data/development/data/english/annotations/bc/cctv/00/cctv_0000.gold_conll"
    with z.open(n) as f:
        lines = [l.decode("utf-8", "replace").rstrip("\n") for l in f]
    sents, clusters = parse_gold_conll(lines)
    sized = sorted(((len(v), k, v) for k, v in clusters.items()), reverse=True)
    print("sents", len(sents), "chains", len(clusters))
    print("--- clusters of size >=3 (the validation) ---")
    shown = 0
    for ln, k, v in sized:
        if ln < 3: continue
        print("  size %2d : %s" % (ln, " | ".join(render(sents, m) for m in v)[:180]))
        shown += 1
        if shown >= 8: break
    print("multi-mention clusters found:", shown)
