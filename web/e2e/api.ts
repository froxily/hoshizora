import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { test as base, type Route } from '@playwright/test';

const API_ROOT = fileURLToPath(new URL('../../api/', import.meta.url));

interface Operation {
  readonly pattern: RegExp;
  readonly body: string;
}

function operations(): Operation[] {
  const spec = readFileSync(`${API_ROOT}openapi.yaml`, 'utf-8').split('\n');
  const found: Operation[] = [];
  let path: string | null = null;
  for (const line of spec) {
    const pathMatch = /^ {2}(\/api\/v1\/\S+):$/.exec(line);
    if (pathMatch?.[1] !== undefined) {
      path = pathMatch[1];
      continue;
    }
    const operationMatch = /^ {6}operationId: (\w+)$/.exec(line);
    if (operationMatch?.[1] !== undefined && path !== null) {
      const template = path.replace(/\{[^}]+\}/g, '[^/]+');
      found.push({
        pattern: new RegExp(`^${template}$`),
        body: readFileSync(
          `${API_ROOT}src/main/resources/openapi/examples/${operationMatch[1]}.json`,
          'utf-8',
        ),
      });
      path = null;
    }
  }
  return found;
}

const OPERATIONS = operations();

export function exampleFor(pathname: string): string | undefined {
  return OPERATIONS.find((operation) => operation.pattern.test(pathname))?.body;
}

export async function answerFromExamples(route: Route): Promise<void> {
  const body = exampleFor(new URL(route.request().url()).pathname);
  await (body === undefined
    ? route.fulfill({
        status: 404,
        contentType: 'application/problem+json',
        body: '{"status":404,"code":"not_found","title":"Not found"}',
      })
    : route.fulfill({ status: 200, contentType: 'application/json', body }));
}

export const test = base.extend<{ errors: string[] }>({
  errors: async ({ page }, provide) => {
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(String(error)));
    page.on('console', (message) => {
      if (message.type() === 'error') {
        errors.push(message.text());
      }
    });
    await provide(errors);
  },
  page: async ({ page }, provide) => {
    await page.route('**/api/v1/**', answerFromExamples);
    await provide(page);
  },
});

export { expect } from '@playwright/test';
