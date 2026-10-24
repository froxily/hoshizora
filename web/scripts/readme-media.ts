import { chromium, devices, type Browser, type Page } from '@playwright/test';
import { execFile } from 'node:child_process';
import { mkdir, rename, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs, promisify } from 'node:util';

const run = promisify(execFile);
const MEDIA = fileURLToPath(new URL('../../docs/media/', import.meta.url));
const OUT = join(MEDIA, 'raw');
const GIF_FILTER =
  'fps=10,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=64:stats_mode=diff[p];[b][p]paletteuse=dither=none:diff_mode=rectangle';
const GIF_START_SECONDS = '5';
const GIF_SECONDS = '19';
const DESKTOP = { width: 1440, height: 900 };
const TOUR = { width: 1280, height: 720 };
const SETTLE_MS = 6_000;
const HEADER_PX = 96;
const GPU_ARGS = ['--enable-gpu', '--ignore-gpu-blocklist', '--use-angle=d3d11'];

interface Capture {
  name: string;
  path: string;
  phone?: boolean;
  scrollTo?: string;
}

const CAPTURES: readonly Capture[] = [
  { name: 'home-en', path: '/en' },
  { name: 'near-earth-ja', path: '/ja/near-earth' },
  { name: 'launches-en', path: '/en/launches', scrollTo: 'Launches per year by national program' },
  { name: 'sun-ja', path: '/ja/sun', scrollTo: 'オーロラが見える可能性' },
  { name: 'agency-jaxa-ja', path: '/ja/agencies/jaxa' },
  { name: 'home-ja-phone', path: '/ja', phone: true },
];

function timeZone(path: string): string {
  return path.startsWith('/ja') ? 'Asia/Tokyo' : 'UTC';
}

async function settle(page: Page, heading?: string): Promise<void> {
  await page.waitForLoadState('networkidle');
  if (heading !== undefined) {
    const box = await page.getByRole('heading', { name: heading }).first().boundingBox();
    await page.mouse.wheel(0, (box?.y ?? HEADER_PX) - HEADER_PX);
  }
  await page.waitForTimeout(SETTLE_MS);
}

async function screenshot(browser: Browser, site: string, capture: Capture): Promise<void> {
  const context = await browser.newContext(
    capture.phone === true
      ? { ...devices['Pixel 7'], timezoneId: timeZone(capture.path) }
      : { viewport: DESKTOP, deviceScaleFactor: 1, timezoneId: timeZone(capture.path) },
  );
  const page = await context.newPage();
  await page.goto(`${site}${capture.path}`);
  await settle(page, capture.scrollTo);
  await page.screenshot({ path: join(OUT, `${capture.name}.png`) });
  await context.close();
}

async function glide(page: Page, pixels: number): Promise<void> {
  for (let moved = 0; moved < pixels; moved += 20) {
    await page.mouse.wheel(0, 20);
    await page.waitForTimeout(16);
  }
}

async function tour(browser: Browser, site: string): Promise<void> {
  const context = await browser.newContext({
    viewport: TOUR,
    timezoneId: 'Asia/Tokyo',
    recordVideo: { dir: OUT, size: TOUR },
  });
  const page = await context.newPage();
  await page.goto(`${site}/en`);
  await settle(page);
  await glide(page, 900);
  await page.waitForTimeout(2_500);
  await page.getByRole('link', { name: 'Read this page in Japanese' }).first().click();
  await page.waitForTimeout(3_000);
  await page
    .getByRole('navigation', { name: 'メイン' })
    .getByRole('link', { name: '太陽' })
    .click();
  await page.waitForTimeout(2_500);
  await glide(page, 1_400);
  await page.waitForTimeout(3_000);
  const video = page.video();
  await context.close();
  if (video !== null) {
    await rename(await video.path(), join(OUT, 'tour.webm'));
  }
}

async function main(): Promise<void> {
  const { values } = parseArgs({ options: { site: { type: 'string' } } });
  if (values.site === undefined) {
    throw new Error('Usage: node scripts/readme-media.ts --site <site origin>');
  }
  const site = values.site.replace(/\/$/, '');
  await rm(OUT, { recursive: true, force: true });
  await mkdir(OUT, { recursive: true });
  const browser = await chromium.launch({ args: GPU_ARGS });
  await (await browser.newPage()).goto(`${site}/en`);
  for (const capture of CAPTURES) {
    await screenshot(browser, site, capture);
  }
  await tour(browser, site);
  await browser.close();
  for (const { name } of CAPTURES) {
    await run('cwebp', [
      '-quiet',
      '-q',
      '82',
      '-m',
      '6',
      join(OUT, `${name}.png`),
      '-o',
      join(MEDIA, `${name}.webp`),
    ]);
  }
  await run('ffmpeg', [
    '-v',
    'error',
    '-y',
    '-ss',
    GIF_START_SECONDS,
    '-t',
    GIF_SECONDS,
    '-i',
    join(OUT, 'tour.webm'),
    '-vf',
    GIF_FILTER,
    join(MEDIA, 'tour.gif'),
  ]);
  console.log(`readme media: ${String(CAPTURES.length)} screenshots and tour.gif in ${MEDIA}`);
}

await main();
