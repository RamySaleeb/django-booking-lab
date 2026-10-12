# Contributing to Slot Studio

Fork the repository, create a focused branch, and follow the README's local setup. Keep changes small and explain the user-visible result in your pull request.

For race-demo JavaScript changes, use Node.js 22+ and run `node --test tests/race.test.cjs` (no npm install needed). Use controlled timers and fake transport responses; do not test failure scenarios against the public deployment.

Before submitting, run `python manage.py test`, `python manage.py check`, and `python manage.py makemigrations --check --dry-run`. Include migrations when the schema changes. Add regression tests for changed booking rules and isolation behavior.

Check booking and cancellation using only a keyboard and at a narrow viewport. Ordinary booking must remain usable without JavaScript. Do not replace the database uniqueness constraint with an availability query; reads cannot arbitrate concurrent writes.

Use fictional data. Do not contribute employer/startup code, credentials, real bookings, or customer information. Discuss new dependencies, authentication, payments, or external services in an issue before expanding the demo.

Useful first contributions: test empty-day layouts, improve focus and large-text coverage, or document local setup on Windows. Larger proposals: PostgreSQL concurrency tests and explicit timezone handling.

## Browser accessibility checks

With the Python virtual environment active and Node.js 22+ installed:

```sh
npm ci
npx playwright install chromium
npm run test:browser
```

On Linux, use `npx playwright install --with-deps chromium` if browser system libraries are missing. Playwright is a development-only dependency; the deployed Django service does not need Node.js. The suite starts Django on `127.0.0.1:18765`, migrates the local SQLite database, and creates fresh anonymous fictional sandboxes. It never targets the public demo. Keep this port free; it deliberately does not reuse an existing server.

The separate `browser` CI job runs the same suite in Chromium. Coverage includes Tab/Enter booking and cancellation with JavaScript both enabled and disabled, visible focus and native fragment destinations, 320px/1280px viewports at 100%/200% root text size, control overflow, accessible button names, and race live-region/focus behavior. Race responses are intercepted locally; real concurrency remains covered by Django tests. Failure traces are retained for seven days in CI.

Automated DOM/live-region assertions do not establish what a screen reader speaks. No manual screen-reader session has been completed for this change, and no WCAG conformance is claimed. A useful follow-up is VoiceOver/Safari and NVDA/Firefox testing: navigate room/day links, reserve/cancel, confirm feedback is read once, then run a race and confirm its result is announced without moving focus. Record the browser, assistive-technology version, and observed speech in your report. Also check browser-native text-only zoom; the suite models text enlargement with a 200% root font size.

## Optional PostgreSQL verification

SQLite remains the default for local development and the free Render demo. PostgreSQL is an opt-in test target, not a production migration. The `postgres` CI job uses an ephemeral PostgreSQL 17 service container and disposable credentials, applies migrations, confirms the backend, and runs the complete booking suite. The SQLite and browser jobs remain separate.

To reproduce locally, activate the Python environment and start an isolated PostgreSQL 17 container (Docker must already be running):

```sh
pip install -r requirements-postgres.txt
docker run --rm --detach --name slot-studio-postgres-test \
  -e POSTGRES_DB=slot_studio_test \
  -e POSTGRES_USER=slot_studio_test \
  -e POSTGRES_PASSWORD=disposable-local-only \
  -p 127.0.0.1:55432:5432 postgres:17
```

Wait until `docker exec slot-studio-postgres-test pg_isready -U slot_studio_test -d slot_studio_test` reports that it accepts connections, then run:

```sh
export PGDATABASE=slot_studio_test
export PGUSER=slot_studio_test
export PGPASSWORD=disposable-local-only
export PGHOST=127.0.0.1
export PGPORT=55432
python manage.py migrate --noinput --settings=config.settings_postgres
python manage.py test booking --noinput --verbosity 2 --settings=config.settings_postgres
```

`PGDATABASE`, `PGUSER`, `PGPASSWORD`, and `PGHOST` are required by the optional settings module; `PGPORT` defaults to `5432`. Django creates and destroys a separate `test_<PGDATABASE>` database, so the disposable role needs permission to create databases. Use only a dedicated local/CI server, never a production database. Stop and discard this test container afterward:

```sh
docker stop slot-studio-postgres-test
unset PGDATABASE PGUSER PGPASSWORD PGHOST PGPORT
```

`requirements-postgres.txt` adds the pinned Psycopg 3 binary adapter; the regular Render requirements and default settings do not change. The configuration uses Django's default READ COMMITTED isolation. It sets a 5-second connection timeout, 10-second lock timeout, and 15-second statement timeout to surface stalled workers. CI has a 10-minute job deadline.

The concurrency tests use a bounded two-party barrier after opening independent connections. PostgreSQL backend process IDs prove separate database sessions. Competing writes to the same sandbox/room/day/hour must produce exactly one reservation and one expected conflict; separate sandboxes must both succeed. Each worker closes its connection in `finally`, and future exceptions propagate to the test runner. No timing sleeps or database mocks are used. The existing cancellation, rebooking, HTTP 201/409, and uniqueness tests run on both backends.

This verifies fixed one-hour slot uniqueness on the tested backends. It does not establish protection for arbitrary-duration overlaps or every isolation level. References: [Django PostgreSQL support and isolation](https://docs.djangoproject.com/en/5.2/ref/databases/#postgresql-notes), [Psycopg installation](https://www.psycopg.org/psycopg3/docs/basic/install.html).
