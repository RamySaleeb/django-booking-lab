const {defineConfig} = require('@playwright/test');
module.exports = defineConfig({
  testDir: './tests/browser',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  use: {baseURL: 'http://127.0.0.1:18765', browserName: 'chromium', channel: process.env.PLAYWRIGHT_CHANNEL || undefined, trace: 'retain-on-failure'},
  webServer: {
    command: 'python manage.py migrate --noinput && python manage.py runserver 127.0.0.1:18765 --noreload',
    url: 'http://127.0.0.1:18765/health/',
    reuseExistingServer: false,
    env: {DJANGO_DEBUG: '1'},
  },
});
