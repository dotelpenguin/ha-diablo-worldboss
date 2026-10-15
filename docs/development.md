# Development

Development takes place on `dev`. The `main` branch contains the installable
Home Assistant integration used for HACS branch downloads. Keep changes on `dev`
until they have passed validation, then merge into `main` for distribution.
Releases are optional; HACS uses the default branch when no release is selected.

## Standalone CLI

The CLI requires Python 3.11 or newer and has no third-party runtime dependencies.
From the repository root:

```sh
PYTHONPATH=src python3 -m diablo_events fetch --pretty
PYTHONPATH=src python3 -m diablo_events watch --interval-minutes 5
PYTHONPATH=src python3 -m diablo_events watch --interval-minutes 120 --count 3
PYTHONPATH=src python3 -m diablo_events fetch --capture /tmp/events.json
PYTHONPATH=src python3 -m diablo_events parse --fixture tests/fixtures/live.json --at 2026-10-14T15:10:00Z --pretty
```

Alternatively, install with `python3 -m pip install -e .` and use `diablo-events`.
JSON goes to stdout and diagnostics to stderr. Exit codes are 0 for complete
results, 1 for failure, 2 for invalid arguments, and 3 for partial or exhausted
coverage. Watch mode continues after recoverable failures; Ctrl-C exits cleanly.
`--count` limits emitted snapshots, including local event transitions.

Captures include source URLs, raw data/errors, and capture time. The supplied
capture path is overwritten. Replay requires a timezone-aware `--at` timestamp.

Schema version 1 includes event state, upcoming events, health, and coverage.
Event times use UTC ISO 8601 strings ending in `Z`; durations are integer seconds.
The `locations` list preserves simultaneous boss/location pairs. At a boss or
Legion spawn time, the next event is selected from `nextTime`. Future boss names
and locations remain unknown until a record provides them. This describes the
next spawn, not the lifetime of the current fight.

Watch retains valid records in memory after failures and marks them stale.
Expired coverage becomes unknown. `last_success_at` is the latest complete
retrieval in this process; cache is not persisted across restarts. Freshness
indicates usable record coverage, not proof of upstream age.

The CLI retries transient network errors and HTTP 429/500/502/503/504 up to three
attempts. Retry-After delays over 30 seconds end the attempt sequence. The Home
Assistant transport instead uses its shared session, coordinated polling, and
rate-limit deferral. See the source files for transport-specific behavior.

## Shared logic and packaging

Canonical parser, schedule, and cache modules live in `src/diablo_events`.
The integration bundles copies to remain self-contained when HACS installs only
`custom_components/diablo_worldboss`. Regenerate after shared changes:

```sh
python3 scripts/sync_shared.py
python3 scripts/validate_repository.py
```

The packaging check verifies one integration, required metadata, icon dimensions,
matching translations/shared modules, and absence of imports from the CLI package.
Tests also enforce matching bundled modules.

## Tests and validation

Create an isolated Python 3.14 environment, install the pinned Home Assistant
runtime, and run:

```sh
python3 -m pip install -r requirements-test.txt
PYTHONPATH=src:. python3 -m unittest discover -s tests -v
```

The baseline is Home Assistant 2026.10.1. Without Home Assistant installed, its
integration tests are skipped; that is not a full validation run. Automated tests
use fixtures and mocks, with no live source dependency.

GitHub Actions defines official HACS and Hassfest checks and the runtime tests
on pushes, pull requests, manual runs, and a weekly schedule. A passing local
packaging check does not establish that those official checks passed.

Before publishing behavior changes, also verify setup, options, restart,
availability, and automation triggers in a running Home Assistant instance.
Update `custom_components/diablo_worldboss/manifest.json` for integration releases.

## HACS repository maintenance

Keep the repository public, with a description, relevant GitHub topics, and an
issue tracker. Suggested topics: `home-assistant`, `hacs`, `diablo4`, and
`custom-integration`. Keep runtime files inside the integration directory.

References: [HACS general requirements](https://www.hacs.xyz/docs/publish/start/),
[integration requirements](https://www.hacs.xyz/docs/publish/integration/).
Listing in the default HACS catalog requires a separate submission; users can
install this repository through Custom repositories.
