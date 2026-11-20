import json
import math
import threading
import unittest
from http.client import HTTPConnection
from unittest.mock import Mock

import observer


class ProjectionTests(unittest.TestCase):
    def test_health_projection_is_allowlisted_fresh_and_null_when_unknown(self):
        from unittest.mock import patch
        receipt = {'observed_at': 10000, 'alerts': ['breaker_open', 'evil_code', 3],
                   'breaker_open': True, 'leased': 1, 'phase_age_s': 7300.5, 'last_finished_age_s': 60,
                   'eligible_queued': 2700, 'materials_fail_streak': 0, 'onedrive_age_s': 600,
                   'active_deferrals': 13, 'persistent_deferrals': 0,
                   'transcription_service': 'active', 'private': 'token'}
        with patch('observer.time.time', return_value=10000):
            health = observer.project({'health_receipt': receipt})['health']
        self.assertEqual(health['alerts'], ['breaker_open'])
        self.assertIs(health['breaker_open'], True)
        self.assertEqual(health['phase_age_s'], 7300.5)
        self.assertEqual(health['eligible_queued'], 2700)
        self.assertNotIn('token', json.dumps(health))
        self.assertNotIn('transcription_service', health)
        with patch('observer.time.time', return_value=20000):
            stale = observer.project({'health_receipt': receipt})['health']
        self.assertIsNone(stale['alerts'])
        self.assertIsNone(stale['observed_at'])
        self.assertIsNone(stale['breaker_open'])
        missing = observer.project({})['health']
        self.assertIsNone(missing['alerts'])
        self.assertIsNone(missing['observed_at'])

    def test_missing_is_null_and_private_nested_data_cannot_escape(self):
        secret = 'https://private.invalid/token?secret=abc'
        raw = {'status': {'materials_total': {'url': secret}}, 'active': [{'title': secret}],
               'units': {secret: secret, 'catalog': secret}, 'time_utc': secret}
        result = observer.project(raw)
        text = json.dumps(result, allow_nan=False)
        self.assertNotIn(secret, text)
        self.assertIsNone(result['pdf']['materials'])
        self.assertIsNone(result['transcription']['done'])
        self.assertIsNone(result['transcription']['current_progress'])
        self.assertEqual(result['transfer'], {'state': 'not_instrumented'})
        self.assertEqual(result['services']['catalog'], 'unknown')
        self.assertIsNone(result['onedrive']['last_observed_at'])


class BoundaryTests(unittest.TestCase):
    def test_scalar_validation(self):
        for bad in (True, -1, float('nan'), float('inf'), '3', {}, [], 1.5):
            with self.subTest(bad=bad):
                self.assertIsNone(observer.project({'disk_free': bad})['storage']['free_bytes'])
        for bad in (True, float('nan'), float('inf'), '0.5', {}):
            self.assertIsNone(observer.project({'active': [{'progress': bad}]})['transcription']['current_progress'])
        self.assertIsNone(observer.project({'active': [{'progress': 2}]})['transcription']['current_progress'])
        self.assertIsNone(observer.project({'active': [{'progress': -1}]})['transcription']['current_progress'])
        raw = {'status': {'transcription_jobs': {'done': 3, 'leased': 1}, 'materials_total': 7,
                          'components': {'index': {'summary': {'source_videos': 4}}}}, 'disk_free': 0}
        projected = observer.project(raw)
        self.assertEqual(projected['transcription']['done'], 3)
        self.assertEqual(projected['transcription']['processing'], 1)
        self.assertEqual(projected['pdf']['materials'], 7)
        self.assertEqual(projected['video']['indexed_objects'], 4)
        self.assertEqual(projected['storage']['free_bytes'], 0)

    def test_existing_fetch_is_bounded_and_fail_closed_http(self):
        from unittest.mock import patch
        import sys
        sys.path.insert(0, str(observer.Path(observer.__file__).resolve().parent.parent))
        with patch('fo_monitor.fetch', return_value={'status': {}}) as fetch:
            observer.fetch_snapshot()
            fetch.assert_called_once_with('oracle-vps', timeout=25)
        for raw in (None, [], {}, 'https://private.invalid'):
            with self.assertRaises(observer.Unavailable):
                observer.SnapshotCache(lambda: raw).get()

    def test_cache_failure_never_returns_stale_or_exception_and_throttles(self):
        fetch = Mock(side_effect=[{'disk_free': 3}, RuntimeError('https://private.invalid')])
        clock = Mock(return_value=0)
        cache = observer.SnapshotCache(fetch, clock=clock)
        self.assertEqual(cache.get()['storage']['free_bytes'], 3)
        clock.return_value = 19
        cache.get()
        self.assertEqual(fetch.call_count, 1)
        clock.return_value = 20
        with self.assertRaises(observer.Unavailable):
            cache.get()
        clock.return_value = 21
        with self.assertRaises(observer.Unavailable):
            cache.get()
        self.assertEqual(fetch.call_count, 2)

    def test_http_boundary_rejects_before_fetch(self):
        fetch = Mock(return_value={'status': {}})
        server = observer.make_server(observer.SnapshotCache(fetch), port=0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            def request(method='GET', path='/api/dashboard', headers=None):
                connection = HTTPConnection('127.0.0.1', server.server_port, timeout=3)
                connection.request(method, path, headers=headers or {'Host': '127.0.0.1:3401'})
                response = connection.getresponse()
                body = response.read()
                result = response.status, dict(response.getheaders()), body
                connection.close()
                return result
            for method in ('POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS', 'HEAD', 'TRACE', 'BREW'):
                self.assertEqual(request(method)[0], 405)
            for path in ('/', '/api/dashboard?x=1', '/api/dashboard/', '//api/dashboard', '/api/%64ashboard'):
                self.assertEqual(request(path=path)[0], 404)
            for headers in ({'Host': 'evil.invalid'}, {'Host': '127.0.0.1:3401', 'Origin': 'https://evil.invalid'},
                            {'Host': '127.0.0.1:3401', 'Origin': 'null'},
                            {'Host': '127.0.0.1:3401', 'Sec-Fetch-Site': 'cross-site'}):
                self.assertEqual(request(headers=headers)[0], 403)
            self.assertEqual(fetch.call_count, 0)
            code, headers, body = request()
            self.assertEqual(code, 200)
            self.assertEqual(headers['Cache-Control'], 'no-store')
            self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
            self.assertNotIn('Access-Control-Allow-Origin', headers)
            self.assertIn('transcription', json.loads(body))
            self.assertEqual(request(headers={'Host': 'localhost:3401', 'Origin': 'http://localhost:3400'})[0], 200)
            self.assertEqual(fetch.call_count, 1)
            with server.cache.lock:
                server.cache.next_poll = float('-inf')
            fetch.side_effect = RuntimeError('https://private.invalid/secret')
            code, headers, body = request()
            self.assertEqual(code, 503)
            self.assertEqual(json.loads(body), {'error': 'observation_unavailable'})
            self.assertNotIn(b'private', body)
            self.assertEqual(headers['Cache-Control'], 'no-store')
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
