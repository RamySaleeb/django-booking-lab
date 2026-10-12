# Contributing to Slot Studio

Fork the repository, create a focused branch, and follow the README's local setup. Keep changes small and explain the user-visible result in your pull request.

For race-demo JavaScript changes, use Node.js 22+ and run `node --test tests/race.test.cjs` (no npm install needed). Use controlled timers and fake transport responses; do not test failure scenarios against the public deployment.

Before submitting, run `python manage.py test`, `python manage.py check`, and `python manage.py makemigrations --check --dry-run`. Include migrations when the schema changes. Add regression tests for changed booking rules and isolation behavior.

Check booking and cancellation using only a keyboard and at a narrow viewport. Ordinary booking must remain usable without JavaScript. Do not replace the database uniqueness constraint with an availability query; reads cannot arbitrate concurrent writes.

Use fictional data. Do not contribute employer/startup code, credentials, real bookings, or customer information. Discuss new dependencies, authentication, payments, or external services in an issue before expanding the demo.

Useful first contributions: test empty-day layouts, improve focus and large-text coverage, or document local setup on Windows. Larger proposals: PostgreSQL concurrency tests and explicit timezone handling.
