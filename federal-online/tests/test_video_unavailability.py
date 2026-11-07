import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portal'))


def test_unavailable_video_does_not_prevent_following_valid_source(tmp_path, monkeypatch, capsys):
    import video_runtime as vr
    monkeypatch.setattr(vr, 'STATE', tmp_path)
    rows=[{'course_url': 'https://example.org/c', 'media_id': str(i), 'status': 'ok',
           'video_stream_url': f'https://example.org/{i}.m3u8', 'duracao_segundos': 30,
           'nome_real_aula': 'aula'} for i in range(2)]
    monkeypatch.setattr(vr, 'rows_from_catalog', lambda: rows)
    def unavailable(candidate, logger):
        raise subprocess.CalledProcessError(1, ['ffprobe'], stderr='HTTP error 404 Not Found')
    calls=[]
    def select(candidate, logger):
        calls.append(candidate)
        return unavailable(candidate, logger)
    monkeypatch.setattr(vr.core, 'choose_stream_selection', select)
    monkeypatch.setattr(vr.core, 'build_candidates', lambda rows, **kwargs: [type('Candidate', (), {})()])
    # VPS-only guard is intentionally preserved; fake only that path's existence.
    exists=Path.exists
    monkeypatch.setattr(Path, 'exists', lambda p: True if str(p)=='/home/ubuntu/anki-vnext' else exists(p))
    vr.main()
    manifest=json.loads((tmp_path/'videos.json').read_text())
    assert len(calls)==2
    assert len(manifest['items'])==2
    assert all(r['status']=='unavailable' and r['reason']=='hls_404' for r in manifest['items'].values())
    assert all(r['retry_at']-r['checked_at']>=86400-1 for r in manifest['items'].values())


def test_authentication_failure_is_not_classified_as_video_unavailable():
    from video_runtime import source_unavailability_reason
    error=subprocess.CalledProcessError(1, ['ffprobe'], stderr='401 Unauthorized token expired 404 Not Found')
    assert source_unavailability_reason(error) is None
