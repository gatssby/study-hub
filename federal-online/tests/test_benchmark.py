import sys
from pathlib import Path
import json
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def test_metrics_measure_insertions_deletions_and_silence_without_asr():
    from fo_hub.benchmark import score
    r=score('a célula tem núcleo','a célula núcleo núcleo',duration_s=60)
    assert r['wer']==0.25
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


def batch():
    return {'synthetic':True,'glossary':['célula'], 'records':[
        {'segment_id':'one','config_id':'baseline','kind':'speech','reference':'célula célula tem núcleo','hypothesis':'célula tem núcleo','duration_s':60,'wall_s':120,'peak_rss_mb':100,
         'anchors':[{'id':'a','reference_start_s':0,'reference_end_s':1,'hypothesis_start_s':1,'hypothesis_end_s':2},{'id':'b','reference_start_s':30,'reference_end_s':31,'hypothesis_start_s':33,'hypothesis_end_s':34}]},
        {'segment_id':'silence','config_id':'baseline','kind':'nonspeech','reference':'','hypothesis':'a b c d a b c d a b c d','duration_s':180}]}


@pytest.mark.parametrize('change', ['missing_gold','empty_gold','duration','nan','duplicate','kind','marker','anchor','bootstrap'])
def test_batch_rejects_invalid_measurements(change):
    from fo_hub.benchmark import score_batch
    data=batch()
    options={}
    if change=='missing_gold': del data['records'][0]['reference']
    if change=='empty_gold': data['records'][0]['reference']=''
    if change=='duration': data['records'][0]['duration_s']=0
    if change=='nan': data['records'][0]['wall_s']=float('nan')
    if change=='duplicate': data['records'].append(data['records'][0].copy())
    if change=='kind': data['records'][0]['kind']='guess'
    if change=='marker': del data['synthetic']
    if change=='anchor': data['records'][0]['anchors'][0]['reference_end_s']=-1
    if change=='bootstrap': options['bootstrap_samples']=0
    with pytest.raises(ValueError): score_batch(data,**options)


def test_batch_cli_and_long_insertion(tmp_path,capsys):
    from fo_hub.benchmark import main
    data=batch()
    data['records'][0]['hypothesis']='célula célula tem núcleo um dois três quatro cinco'
    path=tmp_path/'batch.json'
    path.write_text(json.dumps(data))
    main(['score-batch',str(path),'--bootstrap-samples','10'])
    output=json.loads(capsys.readouterr().out)
    assert output['records'][0]['long_insertions']==1
    assert output['synthetic'] is True


def test_manifest_requires_manual_annotation_and_protocol():
    from fo_hub.benchmark import manifest_readiness
    result=manifest_readiness({'lessons':[],'segments':[]})
    assert not result['ready']
    assert any('teachers' in issue for issue in result['issues'])
    lessons=[{'lesson_id':str(i),'subject':str(i%2),'teacher_id':str(i%2),'manually_verified':True} for i in range(6)]
    segments=[{'id':f'{i}-{stratum}','lesson_id':str(i),'kind':'speech','stratum':stratum,'duration_s':300,'gold_verified':True,'audio_sha256':'a'*64,'manually_verified':True} for i in range(6) for stratum in ('opening','middle_science','noise_interaction')]
    segments += [{'id':f'silence-{i}','kind':'nonspeech','duration_s':180,'gold_verified':True,'audio_sha256':'b'*64,'manually_verified':True} for i in range(2)]
    segments += [{'id':'full','kind':'full_lesson','lesson_id':'0','duration_s':3600,'audio_sha256':'c'*64,'manually_verified':True}]
    manifest={'lessons':lessons,'segments':segments}
    assert manifest_readiness(manifest)['ready']
    lessons[0]['manually_verified']=False
    assert not manifest_readiness(manifest)['ready']


def test_fixture_and_configuration_matrix():
    from fo_hub.benchmark import score_batch
    root=Path(__file__).resolve().parents[1]/'transcription'
    fixture=json.loads((root/'benchmark.synthetic.json').read_text())
    result=score_batch(fixture,bootstrap_samples=20)
    assert result['synthetic'] is True
    assert len(result['comparisons'])==2
    assert result['comparison_ready'] is True
    matrix=json.loads((root/'benchmark-matrix.json').read_text())
    baseline=matrix['configs'][0]
    assert baseline['model']=='large-v3'
    assert baseline['precision']=='FP16'
    assert baseline['vad'] is False
    assert baseline['temperature_fallback'] is False
    assert matrix['configs'][1]['temperature_fallback'] is True
    assert all(c['language']=='pt' and c['threads']==3 for c in matrix['configs'])
    assert [c['beam_size'] for c in matrix['configs']]==[5,5,10]


def test_unpaired_comparisons_are_not_ready_and_full_lesson_is_not_silence():
    from fo_hub.benchmark import score_batch
    data=batch()
    data['records'].append({'segment_id':'long','config_id':'other','kind':'full_lesson','duration_s':3600,'hypothesis':'texto'})
    result=score_batch(data,bootstrap_samples=10)
    assert not result['comparison_ready']
    assert result['records'][-1]['hallucinated_chars_per_minute'] is None
    assert result['records'][-1]['wer'] is None


def test_term_wer_counts_term_substitution_once():
    from fo_hub.benchmark import score_batch
    data={'synthetic':True,'glossary':['célula','núcleo'],'records':[{'segment_id':'s','config_id':'c','kind':'speech','reference':'célula célula','hypothesis':'célula núcleo','duration_s':60}]}
    row=score_batch(data,bootstrap_samples=10)['records'][0]
    assert row['term_recall']==.5
    assert row['term_errors']==1
    assert row['term_wer']==.5


def test_config_summary_pools_timestamps_and_reports_term_errors_and_failures():
    from fo_hub.benchmark import score_batch
    data=batch()
    data['records'][0]['failure']='OOM'
    result=score_batch(data,bootstrap_samples=20)
    summary=result['comparisons'][0]
    assert summary['term_wer']==.5
    assert summary['ts_abs_err_p90_s']==3
    assert summary['repeated_4gram_loops']==1
    assert summary['failures']==[{'segment_id':'one','failure':'OOM'}]
    assert len(summary['cer_ci95'])==2


def test_empty_full_lesson_reference_is_not_nonspeech():
    from fo_hub.benchmark import score_batch
    data={'synthetic':True,'records':[{'segment_id':'long','config_id':'c','kind':'full_lesson','reference':'','hypothesis':'texto','duration_s':3600}]}
    assert score_batch(data,bootstrap_samples=10)['records'][0]['hallucinated_chars_per_minute'] is None


def test_weighted_aggregation_and_bootstrap_not_mean_segment_rates():
    from fo_hub.benchmark import score_batch
    data={'synthetic':True,'records':[
        {'segment_id':'a','config_id':'c','kind':'speech','reference':'a','hypothesis':'b','duration_s':60},
        {'segment_id':'b','config_id':'c','kind':'speech','reference':'a b c','hypothesis':'a b c','duration_s':60}]}
    summary=score_batch(data,bootstrap_samples=100,seed=7)['comparisons'][0]
    assert summary['wer']==.25
    assert summary['wer_ci95']==[0,1]
    assert summary['rtf'] is None
    assert summary['peak_rss_mb'] is None


def test_batch_occurrence_recall_timestamps_resources_and_bootstrap():
    from fo_hub.benchmark import score_batch
    result=score_batch(batch(),bootstrap_samples=100,seed=7)
    assert result['synthetic'] is True
    row=result['records'][0]
    assert row['term_recall']==0.5
    assert row['term_errors']==1
    assert row['term_wer']==0.5
    assert row['ts_abs_err_median_s']==2
    assert row['ts_abs_err_p90_s']==3
    assert row['ts_drift_end_s']==2
    assert row['rtf']==2
    assert row['peak_rss_mb']==100
    assert result['records'][1]['repeated_4gram_loops']==1
    summary=result['comparisons'][0]
    assert summary['wer']==0.25
    assert summary['wer_ci95']==[0.25,0.25]
    assert result==score_batch(batch(),bootstrap_samples=100,seed=7)
