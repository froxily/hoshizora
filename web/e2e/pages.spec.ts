import en from '../src/locales/en/common.json' with { type: 'json' };
import ja from '../src/locales/ja/common.json' with { type: 'json' };
import type { Page } from '@playwright/test';
import { expect, test } from './api';

const CATALOGS = { en, ja } as const;

type Catalog = typeof en;

interface PageCase {
  readonly path: string;
  readonly heading: (catalog: Catalog) => string;
  readonly landmark: (catalog: Catalog) => {
    readonly role: 'heading' | 'button';
    readonly name: string;
  };
}

const section = (name: string) => ({ role: 'heading' as const, name });

const COLLAPSED_BELOW = 1024;

async function openMenuIfCollapsed(page: Page): Promise<void> {
  if ((page.viewportSize()?.width ?? COLLAPSED_BELOW) < COLLAPSED_BELOW) {
    await page.getByRole('button', { name: en.a11y.openMenu }).click();
  }
}

const PAGES: readonly PageCase[] = [
  { path: '', heading: (c) => c.home.title, landmark: (c) => section(c.home.facts.title) },
  {
    path: '/launches',
    heading: (c) => c.pages.launches.title,
    landmark: (c) => section(c.launches.pads.title),
  },
  {
    path: '/near-earth',
    heading: (c) => c.pages.nearEarth.title,
    landmark: (c) => section(c.nearEarth.sentry.title),
  },
  { path: '/sun', heading: (c) => c.pages.sun.title, landmark: (c) => section(c.sun.aurora.title) },
  {
    path: '/exoplanets',
    heading: (c) => c.pages.exoplanets.title,
    landmark: (c) => section(c.exoplanets.nearest.title),
  },
  {
    path: '/agencies',
    heading: (c) => c.pages.agencies.title,
    landmark: (c) => ({ role: 'button', name: c.agencies.types.agency }),
  },
  {
    path: '/agencies/jaxa',
    heading: () => 'JAXA',
    landmark: (c) => section(c.agencies.profile.stats),
  },
  {
    path: '/sources',
    heading: (c) => c.pages.sources.title,
    landmark: (c) => section(c.sources.gaps),
  },
];

for (const locale of ['en', 'ja'] as const) {
  const catalog = CATALOGS[locale];
  for (const page of PAGES) {
    test(`${locale}${page.path || '/'} renders with live data`, async ({
      page: browser,
      errors,
    }) => {
      await browser.goto(`/${locale}${page.path}`);

      await expect(browser.locator('html')).toHaveAttribute('lang', locale);
      await expect(browser.getByRole('heading', { level: 1 })).toContainText(page.heading(catalog));
      const landmark = page.landmark(catalog);
      await expect(browser.getByRole(landmark.role, { name: landmark.name }).first()).toBeVisible();
      await expect(browser.getByText(catalog.dataLink.live)).toBeAttached();
      await expect(browser.getByText(catalog.dataLink.waking)).toHaveCount(0);
      expect(errors).toEqual([]);
    });
  }
}

test('the language toggle keeps the page and switches the language', async ({ page }) => {
  await page.goto('/en/near-earth');
  await openMenuIfCollapsed(page);
  await page
    .getByRole('link', { name: 'Read this page in Japanese' })
    .filter({ visible: true })
    .first()
    .click();

  await expect(page).toHaveURL(/\/ja\/near-earth$/);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(ja.pages.nearEarth.title);
});

test('every chart can be read as a table', async ({ page }) => {
  await page.goto('/en/launches');
  const toggle = page.getByRole('button', { name: en.chart.table }).first();

  await toggle.click();

  await expect(toggle).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('table').first()).toBeVisible();
});

test('reduced motion is remembered across pages', async ({ page }) => {
  await page.goto('/en');
  await openMenuIfCollapsed(page);
  await page
    .getByRole('button', { name: en.motion.reduce })
    .filter({ visible: true })
    .first()
    .click();
  await page.goto('/en/sun');

  await expect(page.locator('html')).toHaveAttribute('data-motion', 'reduced');
  await openMenuIfCollapsed(page);
  await expect(
    page.getByRole('button', { name: en.motion.reduce }).filter({ visible: true }).first(),
  ).toHaveAttribute('aria-pressed', 'true');
});

test('without WebGL the hero keeps its still poster', async ({ page }) => {
  await page.goto('/en');

  await expect(page.getByRole('heading', { level: 1 })).toHaveText(en.home.title);
  await expect(page.locator('section svg[viewBox="0 0 1600 900"]').first()).toBeAttached();
  await expect(page.locator('canvas')).toHaveCount(0);
});
