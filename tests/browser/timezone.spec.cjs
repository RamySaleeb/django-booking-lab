const {test, expect} = require('@playwright/test');

test('explicit device timezone and local labels preserve UTC booking', async ({browser}) => {
  const context = await browser.newContext({timezoneId: 'Asia/Kolkata'});
  const page = await context.newPage();
  await page.goto('/');
  await expect(page.getByLabel('Display timezone', {exact:true})).toHaveValue('UTC');
  await page.getByRole('button', {name:'Use device timezone'}).click();
  await expect(page.getByLabel('Display timezone', {exact:true})).toHaveValue(/^Asia\/(Kolkata|Calcutta)$/);
  const slot = page.locator('.slot').first();
  await expect(slot).toContainText('09:00 – 10:00 UTC');
  await expect(slot).toContainText('14:30 UTC+05:30');
  await slot.click();
  await expect(page.locator('.reservation')).toContainText('09:00 UTC');
  await expect(page.locator('.reservation')).toContainText('14:30 UTC+05:30');
  await expect(page.getByLabel('Display timezone', {exact:true})).toHaveValue(/^Asia\/(Kolkata|Calcutta)$/);
  await page.getByRole('button', {name:/^Cancel Focus room/}).click();
  await expect(page.getByLabel('Display timezone', {exact:true})).toHaveValue(/^Asia\/(Kolkata|Calcutta)$/);
  await expect(page.locator('.reservation')).toHaveCount(0);
  await context.close();
});

test('timezone selection works without JavaScript at 320px and 200% text', async ({browser}) => {
  const context = await browser.newContext({javaScriptEnabled:false, viewport:{width:320,height:900}});
  const page = await context.newPage();
  await page.route('**/static/app.css', async route => {
    const response = await route.fetch();
    await route.fulfill({response, body:(await response.text()) + '\nhtml {font-size:200%}'});
  });
  await page.goto('/');
  await expect(page.getByRole('button',{name:'Use device timezone'})).toBeHidden();
  await page.getByLabel('Display timezone',{exact:true}).selectOption('Pacific/Kiritimati');
  await page.getByRole('button',{name:'Apply timezone',exact:true}).press('Enter');
  await expect(page).toHaveURL(/timezone=Pacific%2FKiritimati/);
  await expect(page.getByLabel('Display timezone',{exact:true})).toHaveValue('Pacific/Kiritimati');

  await expect(page.locator('.slot').last()).toContainText('06:00 UTC+14:00');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBe(320);
  await page.locator('.slot').first().click();
  await expect(page.locator('.reservation')).toContainText('Pacific/Kiritimati');
  await page.getByRole('button',{name:/^Cancel Focus room/}).click();
  await expect(page.locator('.reservation')).toHaveCount(0);
  await context.close();
});
