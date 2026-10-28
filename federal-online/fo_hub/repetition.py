"""Text-only repetition candidates; no acoustic diagnosis or automatic deletion."""
from __future__ import annotations

from collections import Counter
import math
import re
import unicodedata

_TOKEN = re.compile(r'[+−-]?\d+(?:[.,]\d+)?|\w[\w\u0300-\u036f]*|[=<>±×÷%+−-]', re.UNICODE)


def repetition_candidates(segments, max_word_run=4, max_phrase_tokens=64, gap_s:float=20.0):
    """Find maximal disjoint tandem runs, including runs split by decoder rows.

    Multi-token phrases require >=3 occurrences; single tokens require more
    than max_word_run. A gap longer than gap_s breaks a run. The 64-token
    phrase bound is explicit, not a guarantee to detect every possible loop.
    Minute counts use the ORIGINAL SEGMENT START, not fabricated token timing.
    Candidates may be legitimate teaching: keep all text and request review.
    """
    tokens=[]; blocks=[]; block_start=0; previous_end=None
    minute_totals=Counter(); minute_candidates=Counter()
    for idx, segment in enumerate(segments):
        start,end=float(segment['start']),float(segment['end'])
        valid=math.isfinite(start) and math.isfinite(end) and start>=0 and end>=start
        if not valid or (previous_end is not None and start-previous_end>gap_s):
            if len(tokens)>block_start:blocks.append((block_start,len(tokens)))
            block_start=len(tokens)
        minute=int(start//60) if valid else None
        words=_TOKEN.findall(unicodedata.normalize('NFC',str(segment.get('text',''))).casefold())
        tokens.extend((word,idx,minute) for word in words)
        minute_totals[minute]+=len(words)
        if not valid:
            if len(tokens)>block_start:blocks.append((block_start,len(tokens)))
            block_start=len(tokens)
        previous_end=end if valid else None
    if len(tokens)>block_start:blocks.append((block_start,len(tokens)))
    words=[t[0] for t in tokens]
    flags=[]; candidate_count=0
    for lo,hi in blocks:
        pos=lo
        while pos<hi:
            best_end=pos; best_width=0; best_count=0
            for width in range(1,min(max_phrase_tokens,(hi-pos)//3)+1):
                required=max_word_run+1 if width==1 else 3
                if pos+width*required>hi:continue
                phrase=words[pos:pos+width]
                if any(words[pos+k*width:pos+(k+1)*width]!=phrase for k in range(1,required)):
                    continue
                count=required
                while pos+(count+1)*width<=hi and words[pos+count*width:pos+(count+1)*width]==phrase:
                    count+=1
                end=pos+count*width
                if end>best_end:best_end,best_width,best_count=end,width,count
            if best_end==pos:
                pos+=1;continue
            affected=tokens[pos:best_end]
            first,last=affected[0][1],affected[-1][1]
            flags.append({'kind':'token_repetition' if best_width==1 else 'ngram_repetition',
                          'idx':first,'end_idx':last,'start':float(segments[first]['start']),
                          'end':float(segments[last]['end']),'phrase_tokens':best_width,
                          'occurrences':best_count,'words':len(affected),
                          'classification':'requires_acoustic_review'})
            candidate_count+=len(affected)
            minute_candidates.update(t[2] for t in affected)
            pos=best_end
    def bucket_key(value):return -1 if value is None else value
    minutes=[{'minute':m,'total_tokens':minute_totals[m],
              'candidate_tokens':minute_candidates[m]} for m in sorted(minute_totals,key=bucket_key)]
    metrics={'total_tokens':len(tokens),'candidate_tokens':candidate_count,
             'ratio':round(candidate_count/len(tokens),4) if tokens else 0.0,
             'candidate_runs':len(flags),'max_phrase_tokens':max_phrase_tokens,
             'classification':'requires_acoustic_review','minute_policy':'segment_start_not_token_alignment',
             'by_minute':minutes}
    return {'flags':flags,'metrics':metrics}
