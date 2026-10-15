"""Shared last-known event cache."""
from .parser import record
from .schedule import iso, snapshot


class EventCache:
    def __init__(self):
        self.sources = {}
        self.failures = []
        self.last_attempt = None
        self.last_success = None

    def update(self, bundle, now):
        self.last_attempt = now
        self.failures = []
        for kind in ('helltide', 'world_boss', 'legion'):
            entry = bundle.get(kind, {})
            try:
                if not isinstance(entry, dict) or 'error' in entry:
                    raise ValueError('Retrieval failed')
                record(entry.get('data'), kind)
                self.sources[kind] = {**entry, 'retrieved_at': iso(now)}
            except (ValueError, TypeError) as error:
                self.failures.append({'source': kind, 'code': 'refresh_failed', 'message': str(error)})
        if not self.failures:
            self.last_success = now

    def evaluate(self, now):
        result = snapshot(self.sources, now, self.last_attempt)
        if self.failures:
            result['health']['errors'].extend(self.failures)
            result['health']['success'] = False
            result['health']['status'] = 'partial' if self.sources else 'error'
            result['freshness'] = 'stale'
        result['last_success_at'] = iso(self.last_success)
        result['source_retrieved_at'] = {key: value['retrieved_at'] for key, value in self.sources.items()}
        return result

    def next_boundary(self, now):
        candidates = []
        for kind, entry in self.sources.items():
            _, start, end = record(entry['data'], kind)
            candidates.extend(t for t in (start, end) if t > now)
        return min(candidates) if candidates else None
