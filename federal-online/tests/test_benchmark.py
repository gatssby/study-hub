import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def test_metrics_measure_insertions_deletions_and_silence_without_asr():
    from fo_hub.benchmark import score
    r=score('a célula tem núcleo','a célula núcleo núcleo',duration_s=60)
    assert r['wer']==0.25  # one substitution in four reference words
    assert r['reference_words']==4
    s=score('','legenda indevida',duration_s=120)
    assert s['hallucinated_chars_per_minute']==8.0
    assert s['wer'] is None


def test_benchmark_plan_selection_is_reproducible_and_distributed():
    from fo_hub.benchmark import select_lessons
    records=[{'lesson_id':str(i),'subject':s,'duration_s':3600} for i,s in enumerate(['Bio']*5+['Química']*5)]
    a=select_lessons(records,6,seed=20261021)
    assert a==select_lessons(list(reversed(records)),6,seed=20261021)
    assert len({x['lesson_id'] for x in a})==6
    assert len({x['subject'] for x in a})==2
    assert all(x['windows'][1]['start_s']==1650 for x in a)
