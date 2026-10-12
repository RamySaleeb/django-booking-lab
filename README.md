# Slot Studio

**Make room for good work.** An original Python / Django booking showcase by [Ramy Saleeb](https://github.com/RamySaleeb).

Browse three fictional workspaces, reserve an hourly slot, cancel a reservation, and send two competing requests to see double-booking prevention in action. No account or personal details required.

## Try the walkthrough

1. Choose **Focus room**, **Meeting room**, or **Creative studio**.
2. Pick one of the next seven days. Every session lasts one hour; all times are **UTC**.
3. Reserve an open time. It appears under **Your reservations** and becomes unavailable.
4. Cancel it. The slot becomes available again.
5. Click **Test a booking race**. Two real concurrent HTTP requests target the same open slot. Normally one returns `201 Created`; the other returns `409 Conflict`. Click **See updated reservations** to confirm only one booking exists. If the slot was already taken, both requests return `409`.

Each browser gets a signed, anonymous sandbox identifier. Visitors do not compete for the same global rooms, while requests within one sandbox compete for the same database slot. Booking and cancellation work without JavaScript; only the race experiment requires it.

## What this demonstrates

| Concern | Implementation |
| --- | --- |
| Double booking | Database uniqueness across sandbox, room, date, and hour; no check-then-insert race |
| Concurrent requests | Two simultaneous browser POSTs; tests also use two independent database connections |
| Business rules | Listed rooms, 09:00–17:00 hourly slots, next seven UTC days |
| Isolation | Every query and cancellation is scoped to the visitor's signed sandbox |
| Request safety | CSRF-protected POST mutations, UUID references, server-side validation |
| Accessibility | Semantic HTML, keyboard focus indicators, labelled controls, live status, responsive layout |

The view handles HTTP. `booking/services.py` owns booking rules and translates a uniqueness conflict into an expected result. `booking/models.py` owns the final database constraint. Django templates render the interface; a small JavaScript file runs the optional race.

## Run locally

Requires Python 3.14.

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000. On Windows, activate with `.venv\Scripts\activate`.

```sh
python manage.py test
python manage.py check
python manage.py makemigrations --check --dry-run
```

The test suite covers database uniqueness, competing writes, visitor isolation, cancellation ownership, slot validation, CSRF, POST-only mutations, and the server-rendered booking flow. Tests use a separate file-backed SQLite database so threaded tests exercise separate connections.

## Deploy on Render

Create a **free Python web service** from this repository:

- Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- Start: `python manage.py migrate --noinput && gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --threads 4`
- Set `DJANGO_DEBUG=0` and a fresh random `SECRET_KEY` (do not commit it).
- Render supplies `RENDER_EXTERNAL_HOSTNAME`, which is added to allowed hosts.
- Health endpoint: `/health/`.

This is a disposable, single-instance demo. SQLite data disappears on Render restarts or redeploys; free services may sleep when idle. It is not a real reservation system. No email, payments, customer data, public administration, or private/startup source is included.

For production, use durable PostgreSQL storage, authenticated ownership, retention/rate limits, observability, and a product-specific timezone/cancellation policy. A slot uniqueness constraint does not solve overlapping variable-duration bookings; those need a different data model. Test concurrency against the chosen production database before scaling to multiple instances.

## Contribute

See [CONTRIBUTING.md](CONTRIBUTING.md). Good next steps include PostgreSQL CI coverage, timezone display with daylight-saving tests, and automated browser accessibility checks. Please keep the demo easy to run and never commit credentials or real customer data.

## License

MIT. All rooms and reservations are fictional. This repository is an independent portfolio demo, not a claim about a deployed customer system.
