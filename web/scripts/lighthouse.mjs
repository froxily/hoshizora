import { execSync } from 'node:child_process';
import { mkdirSync, readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { chromium } from '@playwright/test';

const BASE = process.env.LIGHTHOUSE_BASE ?? 'http://localhost:4173';
const OUT = new URL('../../logs/lighthouse/', import.meta.url);
const PAGES = [
  'en',
  'ja',
  'en/launches',
  'en/near-earth',
  'en/sun',
  'en/exoplanets',
  'en/agencies',
  'en/agencies/jaxa',
  'en/sources',
];
const PRESETS = { mobile: [], desktop: ['--preset=desktop'] };
const TARGETS = { mobile: 80, desktop: 95, accessibility: 95 };

mkdirSync(OUT, { recursive: true });
const chrome = process.env.CHROME_PATH ?? chromium.executablePath();
const failures = [];

for (const page of PAGES) {
  for (const [preset, flags] of Object.entries(PRESETS)) {
    const report = new URL(`${page.replaceAll('/', '-')}-${preset}.json`, OUT);
    const args = [
      'dlx',
      'lighthouse@13.5.0',
      `${BASE}/${page}`,
      '--quiet',
      '--only-categories=performance,accessibility',
      '--chrome-flags=--headless=new',
      '--output=json',
      `--output-path=${fileURLToPath(report)}`,
      ...(process.env.LIGHTHOUSE_PORT ? [`--port=${process.env.LIGHTHOUSE_PORT}`] : []),
      ...flags,
    ];
    execSync(['pnpm', ...args].map((arg) => JSON.stringify(arg)).join(' '), {
      stdio: 'ignore',
      env: { ...process.env, CHROME_PATH: chrome },
    });
    const { categories } = JSON.parse(readFileSync(report, 'utf-8'));
    const performance = Math.round(categories.performance.score * 100);
    const accessibility = Math.round(categories.accessibility.score * 100);
    console.log(
      `${page.padEnd(20)} ${preset.padEnd(8)} performance ${performance}  accessibility ${accessibility}`,
    );
    if (performance < TARGETS[preset] || accessibility < TARGETS.accessibility) {
      failures.push(`${page} ${preset}`);
    }
  }
}

if (failures.length > 0) {
  console.error(`Below target: ${failures.join(', ')}`);
  process.exit(1);
}
