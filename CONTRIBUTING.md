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
