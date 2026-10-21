"""Reproducible ASR evaluation preparation/scoring. Never reads or transcribes audio.

plan: JSON lesson records -> deterministic selection/windows for human gold.
score: human gold + independently supplied hypothesis -> WER/CER and silence signal.
Actual model runs require separate explicit authorization, never performed here.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path


def normalize(text):
    text=unicodedata.normalize('NFC',text).casefold()
    return ' '.join(re.findall(r'\w+',text,flags=re.UNICODE))


def distance(a,b):
    previous=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        row=[i]
        for j,y in enumerate(b,1):
            row.append(min(row[-1]+1,previous[j]+1,previous[j-1]+(x!=y)))
        previous=row
    return previous[-1]


def score(reference,hypothesis,duration_s=None):
    ref,hyp=normalize(reference),normalize(hypothesis)
    words=ref.split()
    return {'normalization':'NFC casefold word tokens; numeric spelling unchanged',
            'reference_words':len(words),'hypothesis_words':len(hyp.split()),
            'wer':distance(words,hyp.split())/len(words) if words else None,
            'cer':distance(ref,hyp)/len(ref) if ref else None,
            'hallucinated_chars_per_minute':len(hyp)/(duration_s/60) if not ref and duration_s and duration_s>0 else None,
            'inference_executed':False}


def select_lessons(records,count=6,seed=20261021):
    # Hash ordering is independent of input order and Python/random version.
    unique={str(r['lesson_id']):r for r in records if r.get('duration_s') and float(r['duration_s'])>=900}
    groups={}
    for key,row in unique.items():groups.setdefault(row.get('subject') or 'unknown',[]).append(row)
    for rows in groups.values():rows.sort(key=lambda r:hashlib.sha256(f"{seed}|{r['lesson_id']}".encode()).digest())
    chosen=[]
    while len(chosen)<count and any(groups.values()):
        for subject in sorted(groups):
            if groups[subject] and len(chosen)<count:
                r=groups[subject].pop(0);dur=float(r['duration_s'])
                chosen.append({'lesson_id':r['lesson_id'],'subject':subject,'duration_s':dur,
                               'windows':[{'start_s':0,'duration_s':300,'stratum':'opening'},
                                          {'start_s':dur/2-150,'duration_s':300,'stratum':'middle_science'},
                                          {'start_s':dur-300,'duration_s':300,'stratum':'ending_manual_noise_selection_required'}]})
    return chosen


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='mode',required=True)
    plan=sub.add_parser('plan');plan.add_argument('lessons',type=Path);plan.add_argument('--seed',type=int,default=20261021);plan.add_argument('--count',type=int,default=6)
    scoring=sub.add_parser('score');scoring.add_argument('reference',type=Path);scoring.add_argument('hypothesis',type=Path);scoring.add_argument('--duration-s',type=float)
    args=parser.parse_args(argv)
    if args.mode=='plan':
        records=json.loads(args.lessons.read_text());records=records.get('items',[]) if isinstance(records,dict) else records
        output={'seed':args.seed,'inference_executed':False,'human_review_required':True,'lessons':select_lessons(records,args.count,args.seed)}
    else:output=score(args.reference.read_text(),args.hypothesis.read_text(),args.duration_s)
    print(json.dumps(output,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
