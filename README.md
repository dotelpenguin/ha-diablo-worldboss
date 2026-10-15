# Diablo World Events

Track Diablo IV Helltides, world bosses, and Legion events in Home Assistant
using data from [Helltides.com](https://helltides.com/).

See whether a Helltide is active, view upcoming spawn times and boss locations,
and use timestamp sensors in dashboards and automations.

## Requirements

- Home Assistant **2026.10.1 or newer**. Runtime tests use 2026.10.1.
- [HACS](https://www.hacs.xyz/) installed for the recommended installation method.
- Internet access to retrieve event data.

## Install with HACS

This integration is available as a custom repository.

1. Open **HACS** in Home Assistant.
2. Open the top-right menu and select **Custom repositories**.
3. Enter `https://github.com/dotelpenguin/ha-diablo-worldboss` and select
   **Integration** as the type, then add the repository.
4. Find **Diablo World Events** in HACS and download it.
5. **Restart Home Assistant** after the download completes.
6. Open **Settings → Devices & services → Add integration** and search for
   **Diablo World Events**.
7. Choose an update interval and submit. The integration fetches data immediately
   during setup, then refreshes on the selected interval.

No account, API key, YAML configuration, or separate Python installation is needed.

### Manual installation

Copy the `custom_components/diablo_worldboss` directory from this repository into
`<config>/custom_components/diablo_worldboss` in your Home Assistant configuration.
Restart Home Assistant, then follow steps 6–7 above.

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

## Update interval

The default is **5 minutes**; the supported range is **5–120 minutes**. Change it
through the integration's options under **Settings → Devices & services**.
Saving options reloads the integration and fetches new data.

Known event transitions update locally between fetches. A longer interval can
outlast the schedule information supplied by the source. In that case affected
entities become unavailable until a fetch supplies another event. Five minutes
is recommended for regular use.

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

## Data coverage

The integration reads Helltide, world boss, and Legion records. Boss voting
location overrides, Realmwalker events, and a complete long-range schedule are
not currently included. Locations reflect the source records and may differ
from the website's voting-derived display. Cached data does not survive a restart.

This is a community integration, unaffiliated with Blizzard Entertainment or
Helltides.com. Event availability and accuracy depend on the upstream data.

For CLI usage, testing, and repository maintenance, see
[the developer guide](docs/development.md). Source details are in
[the discovery notes](docs/source-discovery.md).
