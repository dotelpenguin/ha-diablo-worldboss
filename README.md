# Diablo events CLI

A CLI-first Python reader for the public event records used by Helltides.com.
Includes a standalone CLI and a custom Home Assistant integration.

Requires Python 3.11 or newer. Run directly from this checkout:

```sh
PYTHONPATH=src python3 -m diablo_events fetch --pretty
PYTHONPATH=src python3 -m diablo_events watch --interval-minutes 5
PYTHONPATH=src python3 -m diablo_events watch --interval-minutes 120 --count 3
PYTHONPATH=src python3 -m diablo_events fetch --pretty --capture /tmp/events.json
PYTHONPATH=src python3 -m diablo_events parse --fixture tests/fixtures/live.json --at 2026-10-14T15:10:00Z --pretty
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Alternatively install with `python3 -m pip install -e .` and use `diablo-events`.
No runtime dependencies are needed for this initial implementation. The transport
uses bounded standard-library HTTP requests in worker threads; it will need a
Home Assistant-owned async session adapter before integration work.

JSON is written to stdout and diagnostics to stderr. Exit codes: 0 complete,
1 failure, 2 invalid arguments, 3 partial or exhausted coverage. Captures contain
source URLs, source data/errors, and capture time. Replay needs a timezone-aware
`--at` timestamp. Captures are overwritten only at the explicitly supplied path.

Output schema version 1 includes Helltide state, next world boss, ordered upcoming
events, health, and per-source coverage. UTC event times end in `Z`; durations are
integer seconds. Boss `locations` preserve all source-reported boss/location
pairs. An event's primary `name` is not necessarily the boss for every location.

At a boss or Legion spawn time, the next event is selected from `nextTime`.
Future boss identity and locations remain unknown until the source supplies them.
This handoff describes the next spawn, not how long the current fight remains active.
An expired Helltide record yields `active: null`, rather than an invented schedule.
Coverage exhaustion or a broken individual source produces partial output.
`last_success_at` describes the latest complete retrieval in the current process.
Watch retains valid records in memory after refresh failures, marks them stale,
and clears stale status after recovery. It does not persist data across restarts. Freshness means usable source coverage, not proof of upstream age.

Current coverage: Helltide, world boss, and Legion. Realmwalker and the full
schedule are not supported. Watch mode emits compact JSON Lines after each poll and at known event boundaries.
The fetch interval accepts 5–120 minutes; local transitions do not trigger HTTP.
`--count` limits emitted snapshots, including boundary updates. Ctrl-C exits cleanly.
Transient network errors and HTTP 429/500/502/503/504 get up to three attempts
with bounded backoff; malformed payloads and other HTTP failures are not retried.
Retry-After delays over 30 seconds end the current attempt sequence.
Persistent storage, longer schedule coverage, and UI comparison remain pending. See
[the discovery notes](docs/source-discovery.md) and [the plan](plan.md).


## Home Assistant installation

1. Copy `custom_components/diablo_worldboss` from this repository into your Home
   Assistant configuration directory under `custom_components/diablo_worldboss`.
2. Restart Home Assistant.
3. Open **Settings → Devices & services → Add integration**, search for
   **Diablo World Events**, and choose a fetch interval from 5 to 120 minutes.
4. Change the interval through the integration's options. Changes reload the entry.

No YAML configuration or separate Python package installation is needed. The
component bundles the same parsing, schedule, and cache code used by the CLI.
After editing canonical modules in `src/diablo_events`, run
`python3 scripts/sync_shared.py`; the tests check that bundled copies match.

Entities on the service device:

- Source health and Helltide active binary sensors.
- Helltide next transition timestamp.
- Next world boss name and spawn timestamp, with all source boss/location pairs
  in attributes. Unknown boss names do not hide a known spawn timestamp.
- Next upcoming event name and timestamp.
- Refresh button, debounced for 30 seconds across entities.

The coordinator uses Home Assistant's HTTP session. Scheduled callbacks update
local state at known event boundaries without delaying the next network poll.
Partial refresh failures retain previously valid records; expired records become
unavailable. Source health turns off for failed, partial, or exhausted results.
Initial setup retries when no source can supply a valid record. Cache is held in
memory and does not survive a restart. Diagnostics can be downloaded from the
integration menu.

A two-hour interval can exceed source coverage. This produces unavailable event
states until the next fetch; choose five minutes for more frequent source data.
The schedule endpoint and boss voting overrides remain outside this version's
supported sources. Manual refresh requests use the same coordinator and honor
rate-limit delays received from the source.

Runtime tests pass against **Home Assistant 2026.10.1 / Python 3.14.8**. Run the
full suite in a Python environment with that Home Assistant version installed:

```sh
PYTHONPATH=src:. python3 -m unittest discover -s tests -v
```

Tests cover shared logic, entities, coordinator failure/recovery, timer cleanup,
interval validation, refresh routing, and unload routing. A complete UI setup,
restart, options reload, and automation smoke test in a running Home Assistant
instance is still pending; this is the initial custom integration release.
# ha-diablo-worldboss
# ha-diablo-worldboss
# ha-diablo-worldboss
# ha-diablo-worldboss
# ha-diablo-worldboss


## HACS development installation

Add `https://github.com/dotelpenguin/ha-diablo-worldboss` under HACS → Custom
repositories, with type **Integration**. Download **Diablo World Events**, restart
Home Assistant, then add the integration under Settings → Devices & services.

Development work is on the `dev` branch. HACS uses the repository's default
branch when no releases are published. For branch-based development installation,
`dev` must be the GitHub default branch; adding a `/tree/dev` URL does not select
that branch in HACS. Otherwise use the manual installation above until a release
is available. Repository default-branch settings are managed separately from
local commits.
