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
    return ' '.join(re.findall(r'[+−-]?\d+(?:[.,]\d+)?|\w+|[=<>±×÷%+−]',text,flags=re.UNICODE))


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
    return {'normalization':'v2 NFC casefold; words, signed decimal numbers and scientific operators preserved',
            'reference_words':len(words),'hypothesis_words':len(hyp.split()),
            'wer':distance(words,hyp.split())/len(words) if words else None,
            'cer':distance(ref,hyp)/len(ref) if ref else None,
            'hallucinated_chars_per_minute':len(hyp)/(duration_s/60) if not ref and duration_s and duration_s>0 else None,
            'inference_executed':False}


def percentile(values, fraction):
    values = sorted(values)
    position = (len(values) - 1) * fraction
    low = int(position)
    high = min(low + 1, len(values) - 1)
    return values[low] + (values[high] - values[low]) * (position - low)


def term_sequence(words, glossary):
    terms = sorted((term.split() for term in glossary), key=lambda term:(-len(term),term))
    result=[]; i=0
    while i<len(words):
        matched=next((term for term in terms if words[i:i+len(term)]==term),None)
        if matched:
            result.append(' '.join(matched));i+=len(matched)
        else: i+=1
    return result


def repetition_loops(words):
    # Count maximal contiguous runs of an identical four-word block, not rotations.
    count = 0
    i = 0
    while i + 12 <= len(words):
        block = words[i:i + 4]
        end = i + 4
        while words[end:end + 4] == block:
            end += 4
        if end - i >= 12:
            count += 1
            i = end
        else:
            i += 1
    return count


def validate_batch(payload, bootstrap_samples):
    import math
    if type(payload.get('synthetic')) is not bool:
        raise ValueError('explicit synthetic boolean required')
    if type(bootstrap_samples) is not int or bootstrap_samples < 1:
        raise ValueError('bootstrap_samples must be positive')
    if not isinstance(payload.get('records'), list) or not payload['records']:
        raise ValueError('nonempty records required')
    seen = set()
    segment_gold = {}
    for row in payload['records']:
        for key in ('segment_id', 'config_id', 'hypothesis'):
            if not isinstance(row.get(key), str) or (key != 'hypothesis' and not row[key]):
                raise ValueError(f'{key} must be a string')
        identity = (row['config_id'], row['segment_id'])
        if identity in seen:
            raise ValueError('duplicate configuration/segment')
        seen.add(identity)
        if row.get('kind') not in ('speech','nonspeech','full_lesson'):
            raise ValueError('kind must be manually annotated')
        for key in ('duration_s','wall_s','peak_rss_mb'):
            value = row.get(key)
            if key != 'duration_s' and value is None:
                continue
            if type(value) not in (int,float) or not math.isfinite(value) or value < 0 or (key=='duration_s' and value==0):
                raise ValueError(f'invalid {key}')
        reference = row.get('reference')
        if row['kind'] != 'full_lesson' and not isinstance(reference,str):
            raise ValueError('missing gold; only full_lesson may omit reference')
        if reference is not None and not isinstance(reference,str):
            raise ValueError('reference must be text or null')
        if row['kind']=='speech' and not normalize(reference):
            raise ValueError('speech requires nonempty gold')
        if row['kind']=='nonspeech' and normalize(reference):
            raise ValueError('nonspeech requires explicitly empty gold')
        gold = (reference,row['duration_s'],row['kind'])
        if row['segment_id'] in segment_gold and segment_gold[row['segment_id']] != gold:
            raise ValueError('same segment must use identical gold/duration/kind')
        segment_gold[row['segment_id']] = gold
        ids = set()
        anchors = row.get('anchors', [])
        if not isinstance(anchors, list):
            raise ValueError('timestamp anchors must be a list')
        for anchor in anchors:
            if not isinstance(anchor, dict):
                raise ValueError('timestamp anchor must be an object')
            if not isinstance(anchor.get('id'), str) or not anchor['id'] or anchor['id'] in ids:
                raise ValueError('timestamp anchor ids must be unique nonempty strings')
            ids.add(anchor['id'])
            for source in ('reference','hypothesis'):
                start,end = (anchor.get(f'{source}_{edge}_s') for edge in ('start','end'))
                if any(type(v) not in (int,float) or not math.isfinite(v) for v in (start,end)) or not 0 <= start <= end <= row['duration_s']:
                    raise ValueError('invalid timestamp anchor')


def score_batch(payload, bootstrap_samples=2000, seed=20261021):
    """Score supplied text only; bootstrap speech segments within each config."""
    import random
    validate_batch(payload, bootstrap_samples)
    rows = []
    glossary = sorted({normalize(term) for term in payload.get('glossary', []) if normalize(term)})
    for record in payload['records']:
        ref = record.get('reference')
        hyp = record['hypothesis']
        words = normalize(ref).split() if ref is not None else []
        hypothesis = normalize(hyp).split()
        row = dict(record)
        row.update(score(ref, hyp, record['duration_s']) if ref is not None else
                   {'wer': None, 'cer': None, 'reference_words': 0, 'hallucinated_chars_per_minute': None})
        if record['kind'] != 'nonspeech':
            row['hallucinated_chars_per_minute'] = None
        ref_terms=term_sequence(words,glossary)
        hyp_terms=term_sequence(hypothesis,glossary)
        gold_terms=len(ref_terms)
        correct_terms=sum(min(ref_terms.count(term),hyp_terms.count(term)) for term in glossary)
        term_errors=distance(ref_terms,hyp_terms)
        row.update(word_errors=distance(words,hypothesis) if ref is not None else None,
                   character_errors=distance(normalize(ref),normalize(hyp)) if ref is not None else None,
                   reference_chars=len(normalize(ref)) if ref is not None else 0,
                   term_occurrences=gold_terms, term_correct=correct_terms,
                   term_errors=term_errors if ref is not None else None,
                   term_recall=correct_terms/gold_terms if gold_terms else None,
                   term_wer=term_errors/gold_terms if gold_terms else None,
                   long_insertions=long_insertions(words,hypothesis) if ref is not None else None,
                   repeated_4gram_loops=repetition_loops(hypothesis),
                   rtf=record['wall_s']/record['duration_s'] if record.get('wall_s') is not None else None,
                   peak_rss_mb=record.get('peak_rss_mb'))
        anchors = record.get('anchors', [])
        errors = [abs(a['hypothesis_'+edge+'_s']-a['reference_'+edge+'_s']) for a in anchors for edge in ('start','end')]
        ordered = sorted(anchors, key=lambda a:a['reference_start_s'])
        drift = ((ordered[-1]['hypothesis_end_s']-ordered[-1]['reference_end_s']) -
                 (ordered[0]['hypothesis_start_s']-ordered[0]['reference_start_s'])) if len(ordered)>1 else None
        row.update(ts_abs_err_median_s=percentile(errors,.5) if errors else None,
                   ts_abs_err_p90_s=percentile(errors,.9) if errors else None, ts_drift_end_s=drift)
        rows.append(row)
    summaries = []
    for config in sorted({r['config_id'] for r in rows}):
        selected = [r for r in rows if r['config_id']==config]
        speech = [r for r in selected if r['kind']=='speech']
        def rate(sample, metric):
            denominator = sum(r['reference_words'] if metric=='wer' else r['reference_chars'] for r in sample)
            return sum(r['word_errors'] if metric=='wer' else r['character_errors'] for r in sample)/denominator if denominator else None
        rng = random.Random(seed)
        samples=[];cer_samples=[]
        if speech:
            for _ in range(bootstrap_samples):
                sample=rng.choices(speech,k=len(speech))
                samples.append(rate(sample,'wer'))
                cer_samples.append(rate(sample,'cer'))
        terms = sum(r['term_occurrences'] for r in speech)
        errors=[abs(a['hypothesis_'+edge+'_s']-a['reference_'+edge+'_s']) for r in selected for a in r.get('anchors',[]) for edge in ('start','end')]
        nonspeech = [r for r in selected if r['kind']=='nonspeech']
        summaries.append({'config_id':config,'wer':rate(speech,'wer'),'cer':rate(speech,'cer'),
                          'cer_ci95':[percentile(cer_samples,.025),percentile(cer_samples,.975)] if cer_samples else None,
                          'term_wer':sum(r['term_errors'] or 0 for r in speech)/terms if terms else None,
                          'ts_abs_err_median_s':percentile(errors,.5) if errors else None,
                          'ts_abs_err_p90_s':percentile(errors,.9) if errors else None,
                          'drift_by_segment':{r['segment_id']:r['ts_drift_end_s'] for r in selected if r['ts_drift_end_s'] is not None},
                          'repeated_4gram_loops':sum(r['repeated_4gram_loops'] for r in selected),
                          'long_insertions':sum(r['long_insertions'] or 0 for r in selected),
                          'failures':[{'segment_id':r['segment_id'],'failure':r['failure']} for r in selected if r.get('failure')],
                          'wer_ci95':[percentile(samples,.025),percentile(samples,.975)] if samples else None,
                          'term_recall':sum(r['term_correct'] for r in speech)/terms if terms else None,
                          'nonspeech_chars_per_min':sum(len(normalize(r['hypothesis'])) for r in nonspeech)/(sum(r['duration_s'] for r in nonspeech)/60) if nonspeech else None,
                          'peak_rss_mb':max((r['peak_rss_mb'] for r in selected if r['peak_rss_mb'] is not None),default=None),
                          'rtf':sum(r['wall_s'] for r in selected)/sum(r['duration_s'] for r in selected) if all(r.get('wall_s') is not None for r in selected) else None})
    coverage = [{r['segment_id'] for r in rows if r['config_id']==s['config_id']} for s in summaries]
    comparison_ready = len(coverage)>1 and all(c==coverage[0] for c in coverage)
    return {'synthetic':payload['synthetic'],'inference_executed':False,'comparison_ready':comparison_ready,'comparison_note':'Identical segment coverage required; CI overlap is descriptive, not proof of equivalence. No automatic winner.','bootstrap':{'unit':'speech segment','samples':bootstrap_samples,'seed':seed,'confidence':.95},'records':rows,'comparisons':summaries}


def long_insertions(reference, hypothesis):
    # Exact minimum-edit alignment; tie order match/substitution, deletion, insertion.
    a,b=reference,hypothesis
    table=[list(range(len(b)+1))]
    for i,x in enumerate(a,1):
        row=[i]
        for j,y in enumerate(b,1):
            row.append(min(table[-1][j-1]+(x!=y),table[-1][j]+1,row[-1]+1))
        table.append(row)
    i,j=len(a),len(b)
    runs=[]; run=0
    while i or j:
        if i and j and table[i][j]==table[i-1][j-1]+(a[i-1]!=b[j-1]):
            runs.append(run);run=0;i-=1;j-=1
        elif i and table[i][j]==table[i-1][j]+1:
            runs.append(run);run=0;i-=1
        else:
            run+=1;j-=1
    runs.append(run)
    return sum(length>=5 for length in runs)


def manifest_readiness(manifest):
    """Metadata-only checklist, not authorization or proof that files exist."""
    lessons=manifest.get('lessons',[]);segments=manifest.get('segments',[])
    issues=[]
    if len({r.get('lesson_id') for r in lessons})<6: issues.append('at least 6 distinct lessons required')
    if len({r.get('teacher_id') for r in lessons if r.get('teacher_id')})<2: issues.append('at least 2 manually identified teachers required')
    if len({r.get('subject') for r in lessons if r.get('subject')})<2: issues.append('at least 2 subjects required')
    if any(r.get('manually_verified') is not True for r in lessons+segments): issues.append('manual teacher/subject/noise/nonspeech annotation required')
    speech=[r for r in segments if r.get('kind')=='speech' and r.get('gold_verified') is True]
    if sum(r.get('duration_s',0) for r in speech)<5400: issues.append('at least 90 minutes verified speech gold required')
    for lesson in lessons:
        strata={r.get('stratum') for r in speech if r.get('lesson_id')==lesson.get('lesson_id') and r.get('duration_s',0)>=300}
        if not {'opening','middle_science','noise_interaction'}<=strata: issues.append(f"three manually selected 5-minute strata required: {lesson.get('lesson_id')}")
    if sum(r.get('kind')=='nonspeech' and r.get('duration_s',0)>=180 and r.get('gold_verified') is True for r in segments)<2: issues.append('two verified 3-minute nonspeech segments required')
    if not any(r.get('kind')=='full_lesson' and r.get('lesson_id') in {x.get('lesson_id') for x in lessons} for r in segments): issues.append('full lesson stability run required')
    if not segments or any(not re.fullmatch('[0-9a-fA-F]{64}',str(r.get('audio_sha256',''))) for r in segments): issues.append('audio SHA-256 required for every segment')
    ids=[r.get('id') for r in segments]
    if len(set(ids))!=len(ids) or any(not x for x in ids): issues.append('unique segment ids required')
    return {'ready':not issues,'issues':issues,'inference_executed':False,'authorization_granted':False,'scope':'metadata only; verify audio, hashes, gold and runtime separately'}


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
    batch_parser=sub.add_parser('score-batch');batch_parser.add_argument('batch',type=Path);batch_parser.add_argument('--bootstrap-samples',type=int,default=2000);batch_parser.add_argument('--seed',type=int,default=20261021)
    readiness=sub.add_parser('check-manifest');readiness.add_argument('manifest',type=Path)
    args=parser.parse_args(argv)
    if args.mode=='score-batch':
        try: output=score_batch(json.loads(args.batch.read_text()),args.bootstrap_samples,args.seed)
        except (ValueError,KeyError,TypeError) as exc: parser.error(str(exc))
    elif args.mode=='check-manifest':
        output=manifest_readiness(json.loads(args.manifest.read_text()))
    elif args.mode=='plan':
        records=json.loads(args.lessons.read_text());records=records.get('items',[]) if isinstance(records,dict) else records
        output={'seed':args.seed,'inference_executed':False,'human_review_required':True,'lessons':select_lessons(records,args.count,args.seed)}
    else:output=score(args.reference.read_text(),args.hypothesis.read_text(),args.duration_s)
    print(json.dumps(output,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
