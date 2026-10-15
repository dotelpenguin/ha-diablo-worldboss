# Diablo IV event tracker: CLI first, Home Assistant second

## Goal and scope

Build a Python client for https://helltides.com, prove its scraping and event
interpretation through a JSON CLI, then reuse that client in a custom Home
Assistant integration. No Home Assistant sensors or controls are implemented
until the CLI acceptance criteria below pass.

Initial scope: Helltide status, next world boss name/location/time, upcoming
events, source health, a configurable fetch interval, and a refresh button.
Target a specific stable Home Assistant 2026 release when integration work begins;
record the tested version and its Python requirement rather than promising
compatibility with every 2026 release.

## Review findings and decisions

- Source discovery is the first dependency. The retrieved public page contains
  event headings but no live event values. Inspect raw HTML, embedded data,
  scripts, and browser network requests to establish how the timers are populated.
  A public JSON endpoint used by the site is preferable to parsing rendered text.
  Endpoint availability, payload format, boss coverage, and event types remain
  unverified. Do not assume an API or hardcode a guessed schedule.
- Valid output means a stable schema with truthful values. Missing or unverified
  information is `null` with a reason; never invent names, locations, or times.
  Home Assistant entities use unknown/unavailable as appropriate.
- Event times are timezone-aware datetimes, serialized as UTC ISO 8601 strings
  ending in `Z`. Time remaining is a duration in seconds, not a datetime.
- Fetch interval is an integer from 5 through 120 minutes, default 5. Event
  transitions must update locally between fetches, including at a two-hour
  interval, using verified schedule data. Stop projecting when coverage expires.
- Keep network fetching, parsing, event selection, and presentation separate.
  The CLI and Home Assistant must use the same client and normalization logic.

## Phase 1: discover and document the source

1. Inspect Helltide, world boss, and upcoming-event views and the public requests
   they make. Check relevant site terms and robots guidance before automation.
2. Record exact URLs, HTTP methods, timestamp units/timezones, response shapes,
   caching behavior, schedule coverage, and whether names/locations are confirmed
   or predicted. Verify any client-side schedule calculations against the UI.
3. Capture small representative fixtures, with retrieval time and provenance.
   Include active/inactive Helltides and multiple upcoming events where available.
4. Choose the least complex reliable transport: public JSON, embedded structured
   data, or HTML parsing. If browser execution is necessary, document its cost and
   feasibility for Home Assistant before adopting it.
5. Document unknowns and source limitations. If required data is unavailable,
   explicitly revise scope before claiming scraping success.

Deliverable: `docs/source-discovery.md` and source fixtures. This phase determines
parser dependencies; do not choose selectors or an endpoint in advance.

## Phase 2: standalone Python client and CLI

Proposed layout:

```text
pyproject.toml
src/diablo_events/
    client.py          # async HTTP, timeouts, response handling
    parser.py          # source-specific extraction
    models.py          # typed normalized records and JSON serialization
    schedule.py        # event selection and time-based state derivation
    cli.py             # command interface only
tests/
    fixtures/
    test_parser.py
    test_schedule.py
    test_cli.py
docs/source-discovery.md
```

Use an async HTTP client reusable by Home Assistant with an injected session and
clock. Select dependencies after discovery. Configure finite timeouts, bounded
retries for transient failures, and a clear user agent. Respect rate-limit and
retry-after responses; prevent overlapping requests and tight retry loops.

Proposed CLI commands (to implement in this phase):

```sh
diablo-events fetch --pretty
diablo-events watch --interval-minutes 5
diablo-events parse --fixture tests/fixtures/sample.json --at 2026-10-14T12:00:00Z
```

- `fetch`: one live retrieval and normalized JSON snapshot.
- `watch`: fetch on the configured interval; emit JSON Lines snapshots at event
  boundaries and after fetch attempts. Local transitions do not trigger HTTP.
- `parse`: replay a captured source payload with a supplied clock, without network.
- JSON goes to stdout; diagnostics go to stderr. Exit codes: 0 for complete valid
  results, 1 for retrieval/parsing failure, 2 for invalid arguments, 3 for partial
  results. Watch continues after recoverable failures and reports each outcome.
- Optional raw-response capture should use an explicit output path and exclude
  credentials/cookies. Include source URL, fetch time, and schema version.

### Normalized JSON contract

Define and document this contract before implementing output:

| Field | Meaning |
| --- | --- |
| `schema_version` | Versioned output contract |
| `source_url` | Source provenance |
| `evaluated_at` | Clock time used to derive current state |
| `last_attempt_at`, `last_success_at` | Retrieval diagnostics |
| `health.success` | Latest attempt retrieved and validated all required data |
| `health.status` | `ok`, `partial`, or `error` |
| `health.error` | Structured error code/message or `null` |
| `freshness` | Fresh/stale status and verified schedule coverage end |
| `helltide.active` | Boolean, or `null` when unknown |
| `helltide.starts_at`, `ends_at`, `next_starts_at` | UTC timestamps or `null` |
| `helltide.seconds_until_transition` | Nonnegative integer or `null` |
| `world_boss` | Next event with name, location, start time, seconds until start, and confidence/provenance; or `null` |
| `upcoming_events` | Ordered list with event type/name/location/start/end where known |

Distinguish a verified empty list from a failed retrieval. Preserve last-known
records after failures with explicit freshness metadata, but do not represent
expired events as current. Decide freshness limits from actual source coverage in
Phase 1. Treat Helltide windows as start-inclusive/end-exclusive; specify the
world-boss handoff rule from source semantics and test it at the exact boundary.

## Phase 3: CLI validation gate

Automated checks:

- Fixture parsing for valid, empty, partial, malformed, and changed source data.
- Timestamp units, timezone conversion, ordering, and duplicate removal.
- Helltide start/end and boss handoff boundaries using a controlled clock.
- Schedule exhaustion and stale cached data, including the 120-minute interval.
- Timeouts, non-success responses, rate limiting, invalid JSON/HTML, and recovery.
- CLI stdout remains machine-readable JSON; errors, exit codes, and interval
  validation follow the documented contract.

Live checks:

- Compare CLI times, names, locations, and active status with the website at the
  same recorded UTC instant; keep evidence and explain discrepancies.
- Observe at least one Helltide transition in watch mode. Verify a world-boss
  rollover live if practical; otherwise mark it fixture-verified and retain a
  pending live check, without claiming full live verification.
- Confirm the selected source provides enough future coverage for long polling
  intervals, or explicitly expose unknown status when it does not.
- Record request counts and failure recovery. Keep live checks separate from
  deterministic tests so routine tests do not depend on the website.

Gate: normalized output matches observed site data, required automated checks
pass, failure/staleness behavior is demonstrated, and any remaining live-check
limitations are reviewed before Home Assistant implementation begins.

## Phase 4: Home Assistant integration

Use `custom_components/diablo_worldboss/` with `manifest.json`, `__init__.py`,
`config_flow.py`, `const.py`, `coordinator.py`, `sensor.py`, `binary_sensor.py`,
`button.py`, `strings.json`, and translations. Package the shared client through
an installable, versioned dependency or documented local packaging strategy;
avoid a second scraper implementation.

- UI configuration and options flow validate the 5–120-minute interval.
- A shared `DataUpdateCoordinator` fetches data for all entities using Home
  Assistant's HTTP session. Handle initial failure/retry and unload cleanly.
- Local scheduled callbacks update states at known event boundaries independently
  of HTTP polling; remove callbacks on unload and replace them after new data.
- Stable unique IDs and a single service device group related entities.
- Refresh button requests a coordinated refresh, with debouncing/rate limits.
- Diagnostics report last attempt/success, freshness, and sanitized errors.
- Partial failures affect only dependent entities where possible. Health remains
  available to report failure; event data becomes unavailable when unreliable.

### Entity mapping

| Entity | State | Attributes |
| --- | --- | --- |
| Source health binary sensor (diagnostic) | On for latest complete valid fetch; off for failure/partial result | Last attempt/success, error, stale status |
| Helltide active binary sensor | On/off when known | Start, end, next start |
| Helltide next transition timestamp sensor | End if active; next start if inactive | Transition type |
| Next world boss sensor | Boss name | Location, spawn time, confidence where supplied |
| Next world boss timestamp sensor | Spawn datetime | Boss name, location |
| Next upcoming event sensor | Event name | Event type, location, start time, bounded upcoming-event list |
| Next upcoming event timestamp sensor | Event start datetime | Event name/type |
| Refresh button | Stateless | Requests immediate source refresh |

Keep sensor state text short; place structured details in attributes. Use
`SensorDeviceClass.TIMESTAMP` for timestamp entities. Prefer timestamp sensors
and dashboard countdowns to writing changing countdown attributes every second.
Unknown boss names must not hide a known spawn time.

## Phase 5: Home Assistant verification and documentation

Test config/options flows, setup retry, coordinator errors and recovery, entity
values/availability, refresh behavior, options changes, local transitions, and
unload cleanup. Install in a development Home Assistant instance at the pinned
release and verify UI setup, automation triggers, timezone display, restart,
and operation with both interval limits.

Document installation, CLI usage/schema, entities, interval behavior, source
limitations, troubleshooting, and tested versions. Consider HACS packaging only
after the local integration works.

## Immediate next step

Start Phase 1 source discovery, capture fixtures, and then implement the minimal
one-shot CLI. Validate live JSON output before adding watch mode or any Home
Assistant code.

## References checked during planning

- Source: https://helltides.com/
- Shared polling/coordinator: https://developers.home-assistant.io/docs/integration_fetching_data/
- Sensor types: https://developers.home-assistant.io/docs/core/entity/sensor/
- UI configuration: https://developers.home-assistant.io/docs/core/integration/config_flow/

## Implementation progress

- Source discovery notes and real fixtures captured; public Firebase event reads
  verified. Full schedule access and rendered UI comparison remain unresolved.
- One-shot `fetch` and offline `parse` CLI implemented with JSON and exit codes.
- Live CLI fetch succeeded; eight deterministic tests pass.
- Multiple simultaneous boss/location pairs are preserved.
- Watch mode, retry/backoff, persistent cache, zone overrides, long-interval
  coverage, and observed live transitions remain pending. The CLI gate has not
  passed; Home Assistant implementation remains deferred.

### Watch milestone

- Watch CLI accepts 5–120-minute intervals and emits JSON Lines at fetches and
  local boundaries; optional count enables finite runs.
- In-memory last-known records retain retrieval timestamps, failure status, and
  coverage expiry. Transient retrieval failures have bounded retries.
- Twelve tests pass, including local transition without HTTP and cache recovery.
- Boss-location override probe returned null. Full schedule coverage, durable
  caching, override merging, UI comparison, and observed live rollovers remain.


### Home Assistant implementation — October 15, 2026

- User reports CLI works and data appears valid; proceeded to integration work.
- Custom component now includes config/options flows, shared coordinator, service
  device, binary sensors, timestamp/name sensors, refresh button, and diagnostics.
- Shared canonical parsing/cache modules are bundled with a synchronization script
  and equality test, avoiding an unpublished runtime package dependency.
- Uses HA-owned aiohttp session, coordinated polling, refresh debounce, rate-limit
  deferral, per-source cache, local boundaries, and unload timer cleanup.
- Runtime checks pass against Home Assistant 2026.10.1 and Python 3.14.8.
- Running-instance UI setup/restart/options/automation checks remain pending.
  Rendered site parity, live rollover observation, broader schedule coverage,
  and boss override merging remain documented limitations.
