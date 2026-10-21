import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portal'))


def test_video_identity_survives_title_and_signed_url_change():
    from video_runtime import identity, revision
    a = {'course_url': 'https://www.federalonline.com.br/portal/curso-aula/c/2027', 'media_id':'42', 'nome_real_aula':'Before', 'video_stream_url':'https://cdn/a.m3u8?token=1', 'duracao_segundos':100}
    b = dict(a, nome_real_aula='Renamed', video_stream_url='https://cdn/a.m3u8?token=2')
    assert identity(a) == identity(b)
    assert revision(a) == revision(b)
    assert revision(a) != revision(dict(a, duracao_segundos=101))


def test_download_budget_preserves_reserve():
    from video_runtime import allowed_bytes
    assert allowed_bytes(10_000, 4_000) == 6_000
    with pytest.raises(RuntimeError): allowed_bytes(3_000, 4_000)


def test_remote_verification_failure_keeps_staged_video(tmp_path):
    from video_runtime import verify_upload
    video = tmp_path / 'lesson.mp4'
    video.write_bytes(b'original')
    calls=[]
    def runner(command, **kwargs):
        calls.append(command)
        raise RuntimeError('network unavailable')
    with pytest.raises(RuntimeError): verify_upload(video, 'onedrive:Federal Online/course/lesson.mp4', runner=runner)
    assert video.read_bytes() == b'original'
    assert '--download' in calls[0]
