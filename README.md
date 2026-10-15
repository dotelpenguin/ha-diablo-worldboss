# Diablo World Events Home Assistant Integration

Track Diablo IV Helltides, world bosses, and Legion events in Home Assistant
using data from [Helltides.com](https://helltides.com/).

See whether a Helltide is active, view upcoming spawn times and boss locations,
and use timestamp sensors in dashboards and automations.

## Developer Note

This is a community project. Suggestions, bug reports, pull requests, and forks
are welcome. CLI tools and testing instructions are in the
[developer guide](docs/development.md).

## Features

- Helltide active status, region, and next transition time.
- Upcoming world boss names, spawn times, and reported locations.
- Upcoming Legion event times.
- Timestamp sensors for dashboards and automations.
- Configurable updates from 5 to 120 minutes, with an immediate fetch at setup.
- Local state changes at known event boundaries between updates.
- A manual refresh button and source-health diagnostics.
- Configuration through the Home Assistant UI.

## Installation

### Via HACS (Recommended)

1. Open **HACS** and choose **Custom repositories** from the top-right menu.
2. Add `https://github.com/dotelpenguin/ha-diablo-worldboss` with type
   **Integration**.
3. Find **Diablo World Events** in HACS and download it.
4. Restart Home Assistant.
5. Add the integration through the UI as described below.

### Manual Installation

1. Copy `custom_components/diablo_worldboss` into your Home Assistant
   `<config>/custom_components` directory.
2. Restart Home Assistant.
3. Add the integration through the UI.

## Configuration

### Initial Setup

1. Go to **Settings → Devices & services**.
2. Select **Add integration** and search for **Diablo World Events**.
3. Set **Update interval (minutes)**. The default is **5**; allowed values are
   **5–120**.
4. Submit. Event data is fetched immediately during setup.

No account, API key, YAML configuration, or separate Python installation is needed.

### Post-Setup Configuration

Open **Settings → Devices & services**, find **Diablo World Events**, and open
its options to change the update interval. Saving options reloads the integration
and fetches new data without restarting Home Assistant.

Known event transitions update locally between fetches. Longer intervals can
outlast the source's known schedule, leaving affected entities unavailable until
another fetch supplies new data. Five minutes is recommended for regular use.

## Entities

All entities are grouped under the **Diablo World Events** device. Entity IDs
may vary if you rename entities or have previously installed the integration.

| Entity | What it shows |
| --- | --- |
| Source health | On when all required sources are usable; off for partial results, fetch failures, or expired event coverage. Attributes include errors and the last attempt/success times. |
| Helltide active | Whether the known Helltide window is active. Attributes include its start, end, next start when known, and zone ID. |
| Helltide next transition | When the active Helltide ends, or when the next known Helltide begins. |
| Next world boss | The source's primary boss name. Attributes preserve all reported boss/location pairs, including simultaneous bosses in different regions. |
| Next world boss time | The next known world boss spawn time, even when its name is not yet available. |
| Next upcoming event | The earliest known upcoming Helltide, world boss, or Legion event. |
| Next upcoming event time | The start time of that upcoming event. |
| Refresh | Request new event data without waiting for the interval. Repeated requests within 30 seconds may be combined. |

Timestamp sensors display in your configured timezone. They represent event
times; they do not count down every second.

## Manual Refresh

Select **Refresh** on the Diablo World Events device to request new data.
Repeated requests within 30 seconds may be combined. Source rate-limit delays
still apply.

## Usage Examples

The entity IDs below are examples. Check **Settings → Devices & services →
Entities** for the IDs created by your installation and adjust them as needed.

### Dashboard Example

Add a manual card to a dashboard with the following configuration:

```yaml
type: entities
title: Diablo World Events
entities:
  - binary_sensor.diablo_world_events_helltide_active
  - sensor.diablo_world_events_helltide_next_transition
  - sensor.diablo_world_events_next_world_boss
  - sensor.diablo_world_events_next_world_boss_time
  - sensor.diablo_world_events_next_upcoming_event
  - sensor.diablo_world_events_next_upcoming_event_time
```

### Refresh Action Example

Use the refresh button from a script or automation action:

```yaml
action: button.press
target:
  entity_id: button.diablo_world_events_refresh
```

## Updates

Download updates through HACS, then restart Home Assistant to load the new code.
For manual installations, replace the integration directory and restart.

## Troubleshooting

**The integration does not appear in Add integration:** confirm the HACS download
completed and restart Home Assistant. Refresh your browser if the list is stale.

**Some entities are unknown or unavailable:** check the Source health attributes.
The source may not yet provide a boss name, location, or future event. Select
**Refresh** to fetch again. A known spawn time can remain available while its
boss name is unknown.

**Source health is off:** inspect its `health.errors` and `last_attempt_at`
attributes. Check Home Assistant's network access and logs, then try Refresh.
The integration retains usable data after a failed fetch, marks it stale, and
stops presenting expired records as current events. Rate-limited requests wait
until the source permits another attempt.

**HACS reports a repository structure error:** use the repository URL above,
without `/tree/dev`. HACS installs from the default branch when no release is
selected; the integration files are available on `main`.

For help, [open an issue](https://github.com/dotelpenguin/ha-diablo-worldboss/issues)
with your Home Assistant version, integration version, and relevant errors.
Diagnostics are available from the integration's menu in Devices & services.

## Known Issues

### Current Limitations

The integration reads Helltide, world boss, and Legion records. Boss voting
location overrides, Realmwalker events, and a complete long-range schedule are
not currently included. Locations reflect the source records and may differ
from the website's voting-derived display. Cached data does not survive a restart.

## FAQ

**Do I need a Helltides.com account?**

No. The integration reads public event records without credentials.

**Why is a spawn time available while the boss name is unknown?**

The source can provide the next spawn time before its name and location are
available. The integration keeps those values separate.

**Why can the displayed boss differ by location?**

The source can report simultaneous bosses in different regions. The name sensor
shows the primary boss; its `locations` attribute contains all reported pairs.

**Does this create a live countdown?**

The time entities are timestamp sensors. They show event times in Home Assistant's
configured timezone rather than updating a countdown every second.

**Can I configure multiple instances?**

The integration supports one configuration entry for the shared public event feed.

## Requirements

- Home Assistant **2026.10.1 or newer**; runtime tests use 2026.10.1.
- [HACS](https://www.hacs.xyz/) for the recommended installation method.
- Internet access to retrieve event data.

## Support

[Report an issue](https://github.com/dotelpenguin/ha-diablo-worldboss/issues) with
your Home Assistant version, integration version, and relevant error details.
See [the developer guide](docs/development.md) for CLI usage and testing, and
[the discovery notes](docs/source-discovery.md) for source behavior.

This is a community integration, unaffiliated with Blizzard Entertainment or
Helltides.com. Event availability and accuracy depend on the upstream data.
