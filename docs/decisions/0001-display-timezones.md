# 0001: Display-only timezones

Status: accepted and implemented following the maintainer's request to add local-time display, tests, and deployment for issue #5.

## Decision

Timezone choice changes labels only. A reservation remains uniquely identified by anonymous sandbox, room, UTC date, and UTC starting hour. The fixed schedule is 09:00–17:00 UTC in one-hour sessions. No database migration or local-time parsing is introduced.

“Today” means the current UTC date. The selectable calendar remains tomorrow through seven days from today in UTC, regardless of the chosen display zone. Calendar headings explicitly say UTC. Each local range shows both dates, times, and numeric UTC offsets; the selected IANA timezone is visible above the slots and on reservation/race details. Canonical UTC labels remain visible. A local date can be earlier or later than the selected UTC date.

The server converts aware UTC endpoints independently using pinned `tzdata` and Python `zoneinfo`. Conversion starts from real instants; nonexistent local times are never accepted as input and repeated local hours never collapse two slot identities. A session lasts 60 elapsed minutes even when local wall-clock labels skip or repeat an hour.

## Visitor choice and fallback

A labelled GET form selects an IANA timezone, defaulting to UTC. Choices travel in room/day links, forms, cancellation redirects, and race refresh links. Invalid or unavailable values normalize to UTC; no arbitrary timezone file path is opened. The URL carries the display preference; it is not saved to an account, cookie, or local storage.

The optional “Use device timezone” button reads the browser's timezone through Intl only when offering the shortcut and applies it only after activation. No geolocation permission, location API, external service, or paid dependency is involved. If JavaScript or detection is unavailable, the server-rendered selector and all ordinary booking/cancellation flows still work.

## Deterministic examples and coverage

| UTC interval | Display zone | Local interval |
| --- | --- | --- |
| 2024-03-10 09:00–10:00 | America/Los_Angeles | 01:00 UTC-08:00 → 03:00 UTC-07:00 (spring gap) |
| 2024-11-03 08:00–09:00 | America/Los_Angeles | 01:00 UTC-07:00 → 01:00 UTC-08:00 (repeated hour) |
| 2024-01-01 09:00–10:00 | Asia/Kolkata | 14:30 → 15:30, UTC+05:30 |
| 2024-01-01 09:00–10:00 | Pacific/Honolulu | Dec 31 23:00 → Jan 1 00:00, UTC-10:00 |
| 2024-01-01 16:00–17:00 | Pacific/Kiritimati | Jan 2 06:00 → 07:00, UTC+14:00 |

The repeated-hour formatter fixture deliberately includes 08:00 UTC; it does not expand the app's 09:00–17:00 booking schedule. Tests also cover invalid timezone fallback, UTC midnight/window boundaries, identical booking identity across timezone changes, conflict detection, cancellation, query propagation, device detection, no-JavaScript operation, and enlarged-text mobile reflow.

## Scope and limits

Implementation consists of a conversion helper, display-only view context, a GET selector with an optional device shortcut, tests, and documentation. SQLite and PostgreSQL suites run the same Python tests; browser tests exercise the local demo. Pinned timezone data should be deliberately updated when civil-time rules change. The Render plan, SQLite runtime database, anonymous sandbox policy, and fixed-duration booking model remain unchanged. Room-local opening hours, personal accounts, and variable-duration overlap rules are separate future decisions.
