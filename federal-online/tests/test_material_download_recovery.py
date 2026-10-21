"""Synthetic regressions for /portal/materiais filter validation and view-only PDF recovery.

No login, network, downloads or ASR. Fakes mirror the live DOM observed 2026-10-21:
rows expose only <a name="btnMaterialView" data-value data-token data-path> (no
btnMaterialDownload); clicking opens #modal1 (pdf.js canvases, hidden download button)
which then intercepts every later click; bytes come from /portal/documento-online-key.
"""
import json
import sys
from pathlib import Path

import pytest

PORTAL = Path(__file__).resolve().parents[1] / "portal"
sys.path.insert(0, str(PORTAL))
import fo_sync_materials_from_portal_materiais as m  # noqa: E402


class Log:
    def __init__(self):
        self.lines = []

    def log(self, msg):
        self.lines.append(msg)


def row(**kw):
    base = dict(position=0, row_id="r", row_text="t", title_text="t", subject_text="S",
                material_type="Notas", raw_date="24/07/2026", action_id="", action_text="",
                action_href="", action_tag="a", action_score=0, data_path="NOTAS.pdf",
                data_token="tok123", data_value="abc")
    base.update(kw)
    return m.PortalRow(**base)


class DiagPage:
    def __init__(self, diag):
        self.diag = diag

    def evaluate(self, script, arg=None):
        return self.diag


def test_intensivo_subject_not_rejected_by_substring_of_shorter_subject():
    page = DiagPage({
        "row_count": 2,
        "visible_subjects": ["Sociologia - Federal", "Sociologia - Federal - Intensivo"],
        "row_subjects": ["Sociologia - Federal - Intensivo", "Sociologia - Federal - Intensivo"],
        "selected_course_text": "", "selected_discipline_text": "",
    })
    m.validate_filtered_results(page, Log(), "Sociologia - Federal - Intensivo")


def test_substring_matches_collapse_even_without_exact_cells():
    page = DiagPage({
        "row_count": 2,
        "visible_subjects": ["Sociologia - Federal", "Sociologia - Federal - Intensivo"],
        "selected_course_text": "", "selected_discipline_text": "",
    })
    m.validate_filtered_results(page, Log(), "Sociologia - Federal - Intensivo")


def test_real_foreign_subject_rows_still_rejected():
    page = DiagPage({
        "row_count": 2,
        "visible_subjects": ["Sociologia - Federal", "Sociologia - Federal - Intensivo"],
        "row_subjects": ["Sociologia - Federal - Intensivo", "Sociologia - Federal"],
        "selected_course_text": "", "selected_discipline_text": "",
    })
    with pytest.raises(RuntimeError, match="incoerente"):
        m.validate_filtered_results(page, Log(), "Sociologia - Federal - Intensivo")


class Resp:
    def __init__(self, status, body, ctype="application/pdf"):
        self.status, self._body = status, body
        self.headers = {"content-type": ctype}
        self.ok = 200 <= status < 300

    def body(self):
        return self._body

    def text(self):
        return self._body.decode()


class Req:
    def __init__(self):
        self.urls = []

    def get(self, url, **kw):
        self.urls.append(url)
        if "documento-online-key" in url:
            return Resp(200, json.dumps({"status": 0, "token": "t2", "url": "https://cdn.example/doc?sig=1",
                                         "arquivo": "NOTAS.pdf"}).encode(), "text/plain")
        return Resp(200, b"%PDF-1.7 fake")


class ModalPage:
    """Native download never fires; an open modal intercepts clicks until dismissed."""
    url = "https://www.federalonline.com.br/portal/materiais"

    def __init__(self):
        self.request = Req()
        self.modal_open = True
        self.evals = []
        self.context = type("C", (), {"pages": [self]})()

    def evaluate(self, script, arg=None):
        self.evals.append(script)
        if "data-dismiss" in script or "modal" in script:
            self.modal_open = False
        return None

    def wait_for_timeout(self, ms):
        pass

    def locator(self, sel):
        raise AssertionError("must not click through the modal")


def test_view_only_row_recovers_pdf_via_document_key_and_dismisses_modal(tmp_path, monkeypatch):
    def native(*a, **k):
        raise m.PlaywrightTimeoutError('Timeout 45000ms exceeded while waiting for event "download"')

    monkeypatch.setattr(m, "download_via_native_download", native)
    page, dest = ModalPage(), tmp_path / "x.pdf"
    cfg = type("Cfg", (), {"download_timeout_ms": 1000})()
    src = m.download_material_row(page, cfg, Log(), "Materiais Exclusivos - Medicina", row(), dest)
    assert dest.read_bytes().startswith(b"%PDF-")
    assert src == "https://cdn.example/doc?sig=1"
    assert not page.modal_open
    key_url = page.request.urls[0]
    assert "documento-online-key" in key_url and "idDocumento=abc" in key_url and "token=tok123" in key_url


def test_document_key_rejects_non_pdf(tmp_path):
    page = ModalPage()
    page.request.get = lambda url, **kw: (
        Resp(200, json.dumps({"status": 0, "url": "https://cdn.example/x"}).encode(), "text/plain")
        if "documento-online-key" in url else Resp(200, b"<html>login</html>", "text/html"))
    dest = tmp_path / "x.pdf"
    assert m.download_via_document_key(page, row(), Log(), dest) is None
    assert not dest.exists()


def test_document_key_failure_does_not_log_signed_urls(tmp_path):
    page=ModalPage();log=Log()
    def failed(*args,**kwargs):
        raise RuntimeError('https://provider/doc?token=PRIVATE_KEY')
    page.request.get=failed
    assert m.download_via_document_key(page,row(),log,tmp_path/'x.pdf') is None
    assert 'PRIVATE_KEY' not in str(log.lines)


def test_view_only_row_never_opens_memory_heavy_pdf_canvas(tmp_path,monkeypatch):
    from types import SimpleNamespace
    calls=[]
    monkeypatch.setattr(m,'download_via_native_download',lambda *a,**k:calls.append('native'))
    view=row(action_name='btnMaterialView')
    page=ModalPage();dest=tmp_path/'view.pdf'
    m.download_material_row(page,SimpleNamespace(download_timeout_ms=1000),Log(),'Medicine',view,dest)
    assert calls==[]
    assert dest.read_bytes().startswith(b'%PDF-')
