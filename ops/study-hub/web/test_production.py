import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import observer
import production


class ProductionTests(unittest.TestCase):
    def test_wsgi_production_origin_and_exact_route_fail_closed(self):
        calls = []
        app = production.DashboardApplication(observer.SnapshotCache(lambda: calls.append(1) or {'disk_free': 4}))
        def request(**changes):
            env = {'REQUEST_METHOD': 'GET', 'PATH_INFO': '/api/dashboard', 'RAW_URI': '/api/dashboard',
                   'QUERY_STRING': '', 'HTTP_HOST': 'localhost', 'HTTP_ORIGIN': 'https://study.gatssby.com.br',
                   'wsgi.input': io.BytesIO()}
            env.update(changes)
            status = []
            body = b''.join(app(env, lambda s, h: status.append((s, dict(h)))))
            return status[0], body
        for changes, code in [({'HTTP_HOST': 'study.gatssby.com.br'}, '403'),
                              ({'HTTP_ORIGIN': 'https://gatssby.com.br'}, '403'),
                              ({'QUERY_STRING': 'x=1'}, '400'),
                              ({'RAW_URI': '//api/dashboard'}, '404'),
                              ({'REQUEST_METHOD': 'POST'}, '405'),
                              ({'CONTENT_LENGTH': '1'}, '400')]:
            self.assertTrue(request(**changes)[0][0].startswith(code))
        self.assertEqual(calls, [])
        (status, headers), body = request()
        self.assertTrue(status.startswith('200'))
        self.assertEqual(headers['Cache-Control'], 'private, no-store')
        self.assertEqual(json.loads(body)['storage']['free_bytes'], 4)
        self.assertLess(len(body), 16384)

    def test_database_counts_current_archive_and_ignored_without_selecting_text(self):
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / 'hub.sqlite3'
            c = sqlite3.connect(db)
            c.executescript('CREATE TABLE lessons(lesson_id TEXT, version INT, present INT);'
                            'CREATE TABLE transcription_jobs(lesson_id TEXT,version INT,state TEXT,progress REAL);'
                            'CREATE TABLE lesson_video_sources(lesson_id TEXT,available INT);')
            c.executemany('INSERT INTO lessons VALUES(?,?,?)', [('a', 2, 1), ('b', 1, 0), ('c', 1, 1)])
            c.executemany('INSERT INTO transcription_jobs VALUES(?,?,?,?)',
                          [('a', 1, 'done', 1), ('a', 2, 'leased', .3), ('b', 1, 'queued', 0), ('c', 1, 'ignored', 0)])
            c.execute('INSERT INTO lesson_video_sources VALUES(?,?)', ('a', 1))
            c.commit(); c.close()
            before = db.read_bytes()
            result = production.read_database(db)
            self.assertEqual(result['queue_scope'], {'active': 1, 'archived': 2, 'ignored': 1})
            self.assertEqual(result['active'], [{'progress': .3}])
            self.assertEqual(result['available_sources'], 1)
            self.assertEqual(db.read_bytes(), before)
            self.assertFalse((Path(d) / 'missing.db').exists())
            with self.assertRaises(sqlite3.Error):
                production.read_database(Path(d) / 'missing.db')

    def test_storage_receipt_is_fresh_bounded_and_scalar_allowlisted(self):
        with patch('observer.time.time', return_value=10000):
            receipt = {'observed_at': 9990, 'available_bytes': 123, 'study_hub_bytes': 42,
                       'temp_bytes': 3, 'whisper_reserve_bytes': 99, 'growth_bytes_per_day': None,
                       'warning': 'low_reserve', 'private': 'token'}
            result = observer.project({'storage_receipt': receipt})['storage']
            self.assertEqual(result['study_hub_bytes'], 42)
            self.assertEqual(result['warning'], 'low_reserve')
            self.assertEqual(result['sample_observed_at'], 9990)
            self.assertNotIn('token', json.dumps(result))
            for timestamp in (0, 10001, float('nan'), '9990'):
                receipt['observed_at'] = timestamp
                stale = observer.project({'storage_receipt': receipt})['storage']
                self.assertIsNone(stale['study_hub_bytes'])
                self.assertIsNone(stale['warning'])
                self.assertIsNone(stale['sample_observed_at'])

    def test_receipt_projection_never_turns_timer_or_start_timestamp_into_success(self):
        raw = {'units': {'onedrive': 'active'}, 'onedrive_receipt': {'updated_at': 123,
               'pdf_sync': 'verified', 'transcript_sync': 'failed', 'error_type': 'private-token'}}
        projected = observer.project(raw)
        self.assertEqual(projected['onedrive']['pdf_sync'], 'verified')
        self.assertEqual(projected['onedrive']['transcript_sync'], 'failed')
        self.assertIsNone(projected['onedrive']['last_observed_at'])
        self.assertNotIn('private-token', json.dumps(projected))
        self.assertIsNone(projected['transcription']['eta_seconds'])


    def test_pipeline_projection_is_allowlisted_and_survives_cache_envelope(self):
        pipeline = {'observed_at': 1, 'transcription': {'comparable_samples': 15, 'median_processing_per_audio': 2.6,
                    'remaining_active_audio_s': 100, 'unknown_duration_jobs': 4, 'ignored_jobs': 178,
                    'eta_seconds': 260, 'eta_low_seconds': 250, 'eta_high_seconds': 270, 'completed_24h': 8,
                    'audio_24h_s': 12801, 'lesson_id': 'fo_secret'},
                    'videos': {'verified': 2997, 'error': 5, 'unavailable': 3, 'other': 0, 'verified_bytes': 9, 'path': 'x'},
                    'onedrive': {'pdf_sync': 'verified', 'transcript_sync': 'failed', 'updated_at': 99.5,
                                 'transcript_files': 12, 'remote_videos': 2253, 'remote_video_bytes': 7, 'inventory_sha256': 'h'},
                    'reviews': [{'discipline': 'Química', 'severity': 'grave', 'reasons': {'bad_timestamp': 2},
                                 'intervals': [[2091.0, 2121.0]], 'state': 'review', 'text': 'SECRET'}] * 30}
        projected = observer.project({'pipeline': pipeline})
        text = json.dumps(projected)
        for leaked in ('fo_secret', 'SECRET', 'inventory_sha256', '"path"'):
            self.assertNotIn(leaked, text)
        self.assertEqual(projected['pace']['eta_seconds'], 260)
        self.assertEqual(projected['pace']['ignored_jobs'], 178)
        self.assertEqual(projected['downloads']['verified'], 2997)
        self.assertEqual(projected['onedrive']['transcript_sync'], 'failed')
        self.assertEqual(projected['onedrive']['last_observed_at'], 99.5)
        self.assertEqual(len(projected['reviews']), 20)
        self.assertEqual(projected['reviews'][0]['reasons'], {'bad_timestamp': 2})
        cache = production.ProjectedCache()
        with patch('production.fetch_local', return_value=projected):
            again = cache.get()
        self.assertEqual(again['pace'], projected['pace'])
        self.assertEqual(again['reviews'], projected['reviews'])
        self.assertLess(len(json.dumps(again)), 16384)
        self.assertIsNone(observer.project({})['pace']['eta_seconds'])


if __name__ == '__main__':
    unittest.main()
