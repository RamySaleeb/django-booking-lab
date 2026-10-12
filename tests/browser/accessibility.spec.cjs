const {test, expect} = require('@playwright/test');

// Navigate using actual Tab presses, never focus() or clicks. Fail on a trap.
async function tabTo(page, target) {
  for (let i = 0; i < 50; i++) {
    if (await target.evaluate(el => el === document.activeElement)) {
      await expect(target).toBeInViewport();
      expect(await target.evaluate(el => getComputedStyle(el).outlineStyle)).not.toBe('none');
      return;
    }
    await page.keyboard.press('Tab');
  }
  throw new Error('Target could not be reached with Tab');
}

async function expectReflow(page, width) {
  const overflow = await page.evaluate(() => {
        const nodes = [...document.querySelectorAll('main *, header *, footer *')];
        return nodes.filter(el => {
          if (!el.getClientRects().length || el.type === 'hidden') return false;
          return el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).display !== 'inline';
        }).map(el => `${el.tagName}.${el.className}`);
      });
  expect(overflow).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width);
}

for (const javaScriptEnabled of [true, false]) {
  test.describe(`keyboard booking; JavaScript ${javaScriptEnabled ? 'on' : 'off'}`, () => {
    test.use({javaScriptEnabled});
    test('skip, choose room and day, reserve, cancel, and continue', async ({page}) => {
      await page.goto('/');
      const skip = page.getByRole('link', {name: 'Skip to booking'});
      await page.keyboard.press('Tab');
      await expect(skip).toBeFocused();
      await expect(skip).toBeInViewport();
      await page.keyboard.press('Enter');
      await expect(page.locator('#booking')).toBeFocused();
      const room = page.locator('#room-meeting');
      await tabTo(page, room);
      await page.keyboard.press('Enter');
      await expect(room).toHaveAttribute('aria-current', 'true');
      await expect(room).toBeFocused();
      const day = page.locator('.days a').nth(1);
      await tabTo(page, day);
      await page.keyboard.press('Enter');
      await expect(day).toHaveAttribute('aria-current', 'date');
      await expect(day).toBeFocused();
      const reserve = page.getByRole('button', {name: '09:00 – 10:00 Reserve ↗', exact: true});
      await tabTo(page, reserve);
      await page.keyboard.press('Enter');
      const feedback = page.locator('#booking-feedback');
      await expect(feedback).toContainText('Reserved.');
      await expect(feedback).toBeFocused();
      await expect(feedback).toHaveAttribute('role', 'status');
      await expect(page.getByRole('button', {name: '09:00 – 10:00 Reserved', exact: true})).toBeDisabled();
      const cancel = page.getByRole('button', {name: /^Cancel Meeting room on/});
      await tabTo(page, cancel);
      await page.keyboard.press('Enter');
      await expect(feedback).toContainText('Reservation cancelled.');
      await expect(feedback).toBeFocused();
      await expect(reserve).toBeEnabled();
      await expect(page.locator('.reservation')).toHaveCount(0);
      await tabTo(page, page.locator('#room-focus'));
    });
  });
}

for (const width of [320, 1280]) {
  for (const textScale of [100, 200]) {
    test(`reflow at ${width}px and ${textScale}% text`, async ({page}) => {
      await page.setViewportSize({width, height: 900});
      await page.addInitScript(scale => {
        document.addEventListener('DOMContentLoaded', () => { document.documentElement.style.fontSize = `${scale}%`; });
      }, textScale);
      await page.goto('/');
      await expectReflow(page, width);
      expect(await page.locator('html').evaluate(el => getComputedStyle(el).fontSize)).toBe(`${16 * textScale / 100}px`);
      const slot = page.getByRole('button', {name: '09:00 – 10:00 Reserve ↗', exact: true});
      await slot.click();
      await expect(page.locator('#booking-feedback')).toContainText('Reserved.');
      const cancel = page.getByRole('button', {name: /^Cancel Focus room on/});
      await expect(cancel).toBeVisible();
      await expectReflow(page, width);
      await cancel.click();
      await expect(page.locator('#booking-feedback')).toContainText('Reservation cancelled.');
    });
  }
}

test('race status is atomic, retains focus, blocks repeats, and exposes next keyboard action', async ({page}) => {
  let requests = 0;
  await page.route('**/reserve/', async route => {
    requests++;
    await route.fulfill({status: requests === 1 ? 201 : 409, contentType: 'application/json', body: '{}'});
  });
  await page.goto('/');
  const button = page.getByRole('button', {name: 'Test a booking race'});
  await tabTo(page, button);
  await page.keyboard.press('Enter');
  const result = page.locator('#race-result');
  await expect(result).toHaveText('Race complete: 1 reservation accepted (201), 1 duplicate rejected (409).');
  await expect(result).toHaveAttribute('role', 'status');
  await expect(result).toHaveAttribute('aria-live', 'polite');
  await expect(result).toHaveAttribute('aria-atomic', 'true');
  await expect(button).toBeFocused();
  await expect(button).toHaveAttribute('aria-disabled', 'true');
  await page.keyboard.press('Enter');
  await page.keyboard.press('Space');
  await page.keyboard.press('Tab');
  await expect(page.getByRole('link', {name: 'Check your reservations →'})).toBeFocused();
  expect(requests).toBe(2);
});
