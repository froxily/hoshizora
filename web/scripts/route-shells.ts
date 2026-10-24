import { mkdir, readFile, rm, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseArgs } from 'node:util';
import {
  renderShell,
  routeHeads,
  SHELL_LOCALES,
  type Agency,
  type ShellCopy,
  type ShellLocale,
} from './routeShells.ts';

const WEB = fileURLToPath(new URL('..', import.meta.url));
const DIST = join(WEB, 'dist');
const OUT = join(WEB, 'dist-shells');
const PAGE_SIZE = 100;
const ATTEMPTS = 4;
const TIMEOUT_MS = 90_000;

interface AgencyPage {
  items: Agency[];
  total_pages: number;
}

async function getJson<T>(url: string, locale: ShellLocale): Promise<T> {
  for (let attempt = 1; ; attempt += 1) {
    try {
      const response = await fetch(url, {
        headers: { 'Accept-Language': locale, Accept: 'application/json' },
        signal: AbortSignal.timeout(TIMEOUT_MS),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${String(response.status)} from ${url}`);
      }
      return (await response.json()) as T;
    } catch (failure) {
      if (attempt === ATTEMPTS) {
        throw failure;
      }
    }
  }
}

async function agencies(api: string, locale: ShellLocale): Promise<Agency[]> {
  const found: Agency[] = [];
  for (let page = 1, pages = 1; page <= pages; page += 1) {
    const url = `${api}/api/v1/agencies?sort=name&size=${String(PAGE_SIZE)}&page=${String(page)}`;
    const body = await getJson<AgencyPage>(url, locale);
    found.push(...body.items.map(({ key, name }) => ({ key, name })));
    pages = body.total_pages;
  }
  return found;
}

async function copyFor(locale: ShellLocale): Promise<ShellCopy> {
  const path = join(WEB, 'src', 'locales', locale, 'common.json');
  return JSON.parse(await readFile(path, 'utf-8')) as ShellCopy;
}

async function main(): Promise<void> {
  const { values } = parseArgs({
    options: { api: { type: 'string' }, site: { type: 'string' } },
  });
  const { api, site } = values;
  if (api === undefined || site === undefined) {
    throw new Error('Usage: node scripts/route-shells.ts --api <API origin> --site <site origin>');
  }
  const template = await readFile(join(DIST, 'index.html'), 'utf-8');
  await rm(OUT, { recursive: true, force: true });
  let written = 0;
  for (const locale of SHELL_LOCALES) {
    const heads = routeHeads(locale, await copyFor(locale), await agencies(api, locale));
    for (const head of heads) {
      const shell = renderShell(template, site.replace(/\/$/, ''), head);
      const file = join(OUT, `depth-${String(shell.depth)}`, shell.blob);
      await mkdir(dirname(file), { recursive: true });
      await writeFile(file, shell.html, 'utf-8');
      written += 1;
    }
  }
  console.log(`route shells: ${String(written)} written to ${OUT}`);
}

await main();
