import { describe, expect, it } from 'vitest';
import { LOCALES, type Locale } from '../i18n/locales';

interface Messages {
  readonly [key: string]: string | Messages;
}

type Catalog = ReadonlyMap<string, ReadonlyMap<string, string>>;

const files = import.meta.glob<Messages>('./*/*.json', { eager: true, import: 'default' });

function flatten(messages: Messages, prefix = ''): [string, string][] {
  return Object.entries(messages).flatMap(([key, value]) => {
    const path = prefix === '' ? key : `${prefix}.${key}`;
    return typeof value === 'string' ? [[path, value]] : flatten(value, path);
  });
}

function catalogFor(locale: Locale): Catalog {
  return new Map(
    Object.entries(files)
      .filter(([file]) => file.startsWith(`./${locale}/`))
      .map(([file, messages]) => [file.slice(`./${locale}/`.length), new Map(flatten(messages))]),
  );
}

function params(message: string): string[] {
  return [...message.matchAll(/\{\{\s*([\w.]+)\s*\}\}/g)].map(([, name]) => name ?? '').sort();
}

const [reference, ...others] = LOCALES.map((locale) => ({ locale, catalog: catalogFor(locale) }));
const namespaces = [...(reference?.catalog.keys() ?? [])].sort();

describe('locale catalogs', () => {
  it('include at least one namespace', () => {
    expect(namespaces.length).toBeGreaterThan(0);
  });

  it.each(others)('$locale ships the same namespaces as the reference locale', ({ catalog }) => {
    expect([...catalog.keys()].sort()).toEqual(namespaces);
  });

  describe.each(namespaces)('namespace %s', (namespace) => {
    const referenceMessages = reference?.catalog.get(namespace) ?? new Map<string, string>();

    it.each(others)('$locale has exactly the same keys', ({ catalog }) => {
      const messages = catalog.get(namespace) ?? new Map<string, string>();
      expect([...messages.keys()].sort()).toEqual([...referenceMessages.keys()].sort());
    });

    it.each(others)('$locale uses the same interpolation params', ({ catalog }) => {
      const messages = catalog.get(namespace) ?? new Map<string, string>();
      for (const [key, message] of referenceMessages) {
        expect(params(messages.get(key) ?? ''), key).toEqual(params(message));
      }
    });

    it.each(LOCALES)('%s has no empty messages', (locale) => {
      const messages = catalogFor(locale).get(namespace) ?? new Map<string, string>();
      const empty = [...messages]
        .filter(([, message]) => message.trim() === '')
        .map(([key]) => key);
      expect(empty).toEqual([]);
    });
  });
});
