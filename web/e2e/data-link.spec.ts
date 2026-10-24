import { test as base } from '@playwright/test';
import en from '../src/locales/en/common.json' with { type: 'json' };
import { answerFromExamples, expect } from './api';

const test = base;

test('a sleeping API shows the waking state, then the data, with the hero running', async ({
  page,
}) => {
  let awake = false;
  await page.route('**/api/v1/**', async (route) => {
    await (awake
      ? answerFromExamples(route)
      : route.fulfill({ status: 503, contentType: 'text/html', body: 'waking' }));
  });

  await page.goto('/en');

  await expect(page.getByRole('heading', { level: 1 })).toHaveText(en.home.title);
  await expect(page.getByText(en.dataLink.waking).first()).toBeVisible();
  await expect(page.getByText(en.dataLink.wakingDetail).first()).toBeVisible();

  awake = true;

  await expect(page.getByText('(2026 TS)').first()).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText(en.dataLink.live)).toBeAttached();
  await expect(page.getByText(en.dataLink.waking)).toHaveCount(0);
});

test('an HTML wake page from a proxy counts as waking, never as an error', async ({ page }) => {
  await page.route('**/api/v1/**', (route) =>
    route.fulfill({ status: 200, contentType: 'text/html', body: '<html>Starting…</html>' }),
  );

  await page.goto('/en/sun');

  await expect(page.getByText(en.dataLink.waking).first()).toBeVisible();
  await expect(page.getByText(en.dataLink.failed)).toHaveCount(0);
});
