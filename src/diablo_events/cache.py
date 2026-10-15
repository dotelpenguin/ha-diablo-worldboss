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
                if not isinstance(entry, dict):
                    raise ValueError('Invalid source envelope')
                if 'error' in entry:
                    error = entry['error']
                    raise ValueError(error.get('message', error.get('code', 'Retrieval failed')) if isinstance(error, dict) else str(error))
                record(entry.get('data'), kind)
                self.sources[kind] = {**entry, 'retrieved_at': iso(now)}
            except (ValueError, TypeError) as error:
                self.failures.append({'source': kind, 'code': 'refresh_failed', 'message': str(error)})
        if not self.failures:
            self.last_success = now

    def evaluate(self, now):
        result = snapshot(self.sources, now, self.last_attempt)
        if self.failures:
            failed_sources = {error['source'] for error in self.failures}
            result['health']['errors'] = [error for error in result['health']['errors']
                                          if not (error['code'] == 'invalid_source' and error['source'] in failed_sources)]
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
