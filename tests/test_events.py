import asyncio
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from diablo_events.cli import main
from diablo_events.client import fetch
from diablo_events.parser import timestamp
from diablo_events.schedule import snapshot

FIXTURE = Path(__file__).parent / 'fixtures/live.json'


class EventsTest(unittest.TestCase):
    def setUp(self):
        self.envelope = json.loads(FIXTURE.read_text())
        self.bundle = self.envelope['sources']
        self.fetched = timestamp(self.envelope['captured_at'])

    def at(self, when):
        return snapshot(self.bundle, timestamp(when), self.fetched)

    def test_helltide_boundaries(self):
        self.assertFalse(self.at('2026-10-14T14:59:59Z')['helltide']['active'])
        self.assertTrue(self.at('2026-10-14T15:00:00Z')['helltide']['active'])
        self.assertEqual(self.at('2026-10-14T15:54:59Z')['helltide']['seconds_until_transition'], 1)
        expired = self.at('2026-10-14T15:55:00Z')
        self.assertIsNone(expired['helltide']['active'])
        self.assertEqual(expired['health']['status'], 'partial')

    def test_boss_identity_handoff(self):
        before = self.at('2026-10-14T16:29:59Z')['world_boss']
        self.assertEqual(before['name'], 'Ashava')
        self.assertEqual(len(before['locations']), 2)
        after = self.at('2026-10-14T16:30:00Z')['world_boss']
        self.assertIsNone(after['name'])
        self.assertEqual(after['locations'], [])
        self.assertEqual(after['starts_at'], '2026-10-14T20:00:00Z')
        self.assertIsNone(self.at('2026-10-14T20:00:00Z')['world_boss'])

    def test_invalid_source_does_not_hide_others(self):
        self.bundle['helltide']['data']['endTime'] = 'changed'
        result = self.at('2026-10-14T15:10:00Z')
        self.assertIsNone(result['helltide'])
        self.assertEqual(result['world_boss']['name'], 'Ashava')
        self.assertFalse(result['health']['success'])

    def test_timezone_and_naive_rejection(self):
        self.assertEqual(timestamp('2026-10-14T11:00:00-04:00'), timestamp('2026-10-14T15:00:00Z'))
        with self.assertRaises(ValueError):
            timestamp('2026-10-14T15:00:00')

    def test_empty_and_rejected_records(self):
        for value in (None, [], {'error': 'Permission denied'}, {'startTime': '2026-10-14T15:00:00Z', 'nextTime': '2026-10-14T14:00:00Z'}):
            bundle = deepcopy(self.bundle)
            for source in bundle.values():
                source['data'] = value
            self.assertEqual(snapshot(bundle, timestamp('2026-10-14T15:10:00Z'), self.fetched)['health']['status'], 'error')

    def test_cli_json_and_exit(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(['parse', '--fixture', str(FIXTURE), '--at', '2026-10-14T15:10:00Z'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.getvalue())['health']['status'], 'ok')
        self.assertEqual(err.getvalue(), '')
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(['parse', '--fixture', str(FIXTURE), '--at', '2026-10-14T20:00:00Z'])
        self.assertEqual(code, 3)
        self.assertEqual(json.loads(out.getvalue())['upcoming_events'], [])

    def test_fetch_failure_envelope(self):
        with patch('diablo_events.client.get_json', side_effect=TimeoutError('timeout')):
            result = asyncio.run(fetch())
        self.assertEqual(set(result), {'helltide', 'world_boss', 'legion'})
        self.assertTrue(all('error' in entry for entry in result.values()))

    def test_malformed_fixture_is_json_error(self):
        out, err = io.StringIO(), io.StringIO()
        with patch('pathlib.Path.read_text', return_value='[]'), redirect_stdout(out), redirect_stderr(err):
            code = main(['parse', '--fixture', 'bad.json', '--at', '2026-10-14T15:10:00Z'])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out.getvalue())['health']['status'], 'error')



class WatchTest(unittest.TestCase):
    def setUp(self):
        from diablo_events.watch import EventCache
        self.cache = EventCache()
        self.bundle = json.loads(FIXTURE.read_text())['sources']
        self.now = timestamp('2026-10-14T14:59:00Z')

    def test_cache_failure_recovery_and_expiry(self):
        self.cache.update(self.bundle, self.now)
        success = self.cache.evaluate(self.now)['last_success_at']
        self.cache.update({}, timestamp('2026-10-14T15:01:00Z'))
        result = self.cache.evaluate(timestamp('2026-10-14T15:02:00Z'))
        self.assertTrue(result['helltide']['active'])
        self.assertFalse(result['health']['success'])
        self.assertEqual(result['freshness'], 'stale')
        self.assertEqual(result['last_success_at'], success)
        self.assertIsNone(self.cache.evaluate(timestamp('2026-10-14T15:55:00Z'))['helltide']['active'])
        self.cache.update(self.bundle, timestamp('2026-10-14T15:03:00Z'))
        self.assertTrue(self.cache.evaluate(timestamp('2026-10-14T15:03:00Z'))['health']['success'])

    def test_boundary_does_not_fetch(self):
        from datetime import timedelta
        from diablo_events.watch import watch
        current = [self.now]
        elapsed = [0.0]
        calls, output = [], []
        async def fetcher():
            calls.append(True)
            return self.bundle
        async def sleep(seconds):
            current[0] += timedelta(seconds=seconds)
            elapsed[0] += seconds
        asyncio.run(watch(120, count=2, fetcher=fetcher, emit=output.append,
                          clock=lambda: current[0], monotonic=lambda: elapsed[0], sleep=sleep))
        self.assertEqual(len(calls), 1)
        self.assertFalse(output[0]['helltide']['active'])
        self.assertTrue(output[1]['helltide']['active'])

    def test_interval_limits(self):
        from diablo_events.cli import interval
        import argparse
        for value in ('5', '120'):
            self.assertEqual(interval(value), int(value))
        for value in ('4', '121'):
            with self.assertRaises(argparse.ArgumentTypeError):
                interval(value)

    def test_retry_policy(self):
        from diablo_events.client import retry_delay
        from urllib.error import HTTPError
        self.assertEqual(retry_delay(TimeoutError(), 1), 2)
        self.assertIsNone(retry_delay(ValueError(), 0))
        self.assertIsNone(retry_delay(HTTPError('url', 403, 'denied', {}, None), 0))
        self.assertEqual(retry_delay(HTTPError('url', 429, 'limited', {'Retry-After': '10'}, None), 0), 10)
        self.assertIsNone(retry_delay(HTTPError('url', 429, 'limited', {'Retry-After': '120'}, None), 0))


class BundledLogicTest(unittest.TestCase):
    def test_shared_modules_are_identical(self):
        root = Path(__file__).resolve().parents[1]
        for name in ('parser.py', 'schedule.py', 'cache.py'):
            self.assertEqual((root / 'src/diablo_events' / name).read_text(),
                             (root / 'custom_components/diablo_worldboss/lib' / name).read_text())


if __name__ == '__main__':
    unittest.main()
