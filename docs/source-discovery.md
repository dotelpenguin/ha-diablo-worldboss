# Source discovery — October 14, 2026

## Verified transport

The homepage is a Nuxt application. Its initial HTML contains configuration and
empty event stores; its widgets populate records through Firebase subscriptions.
The site configuration lists three read replicas. This prototype uses the first:

`https://helltides-7e530-r1.firebaseio.com`

Only individual public event paths were read, without authentication or cookies:

| GET path | Verified fields | CLI use |
| --- | --- | --- |
| `/helltide.json` | `startTime`, `endTime`, `zone`, `id` | Active window |
| `/world_boss.json` | `boss`, `startTime`, `nextTime`, `zone`, `id` | Next spawn and multiple boss/location pairs |
| `/legion.json` | `startTime`, `nextTime`, `zoneWindow`, `id` | Upcoming Legion time; location unknown |

Timestamps are ISO 8601 UTC strings with millisecond precision. Numeric IDs appear
to match epoch seconds but are not used as event timestamps. Unknown extra fields
are tolerated. Missing records, rejected records, invalid timestamps, and
non-increasing boundaries are rejected per source.

Evidence: homepage bundle `/_nuxt/fMABvsqe.js`, home-page module
`/_nuxt/OiwYXlCd.js`, and widget module `/_nuxt/BMcotOoy.js`. The widget subscribes
to `world_boss`, `world_boss_zone`, `helltide`, and `legion`. Boss zone overrides
are not fetched yet; location output is explicitly the main record's value and
may differ from the site's current voting-derived display.

The source record had Ashava in Scosglen and Avarice in Nahantu at the same spawn
time. Preserve the entire `zone` array rather than treating it as one location.
The source reports these values; their confidence/prediction status is not yet
verified. Do not label them confirmed game observations.

## Limited future coverage

Helltide supplies one window. Boss and Legion supply a start and a next time, not
a complete sequence with future identities. At an exact start boundary the CLI
hands off to `nextTime`; once that time is reached it requires a fresh record.
Helltide is start-inclusive and end-exclusive. It cannot safely support two-hour
polling without unknown periods using these records alone.

`/_nuxt/fGAyXZNN.js` uses `GET /api/schedule`; that request returned a Cloudflare
challenge HTML page during discovery. No challenge bypass was attempted.
A direct `/realmwalker.json` probe returned permission denied; it is excluded
from runtime requests. Its path was exploratory, not verified widget behavior.

There is no documented API stability guarantee or established caching contract.
Runtime requests have a 15-second timeout and a 1 MB response limit. Transient failures now receive up to three attempts with bounded backoff.
Replica failover is not implemented.

## Capture and checks

`tests/fixtures/live.json` preserves three real public records and a capture
assembly timestamp (requests were sequential, not an atomic snapshot).
The live CLI successfully fetched all three sources and emitted JSON with health
`ok`. Automated tests verify state boundaries, partial failures, fixture errors,
timezone normalization, and timeout envelopes. Tests do not access the network.

Source parity is verified against retrieved records and the site's widget code,
not against a rendered browser UI or observed game events. Live Helltide and boss
rollovers still need observation; the complete CLI gate is not passed yet.

## Site guidance checked

- https://helltides.com/terms was read during discovery.
- https://helltides.com/robots.txt returned a JSON 404 response.

These checks do not establish a supported API or permission for redistribution.
Keep requests limited to necessary public records.

## Next work

1. Compare output with the rendered website, including `world_boss_zone` overrides.
2. Investigate publicly accessible schedule coverage without bypassing challenges.
3. Add watch mode with local transitions, 5–120-minute validation, bounded retry
   behavior, and last-known data semantics.
4. Observe a live Helltide transition and source recovery before the HA phase.

## Watch milestone

Watch mode and in-memory per-source caching are implemented. Twelve tests pass,
including a controlled-clock transition with no additional HTTP request and cache
failure/recovery/expiry. The public `world_boss_zone` override returned `null`
during the follow-up check; override merging remains pending a usable sample.
Live observation and rendered UI comparison are still pending.
