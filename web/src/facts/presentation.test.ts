import { describe, expect, it } from 'vitest';
import { figureFor } from './figure';
import { MODULE_ACCENTS, PRESENTATIONS } from './presentation';

const templates = import.meta.glob<string>('../../../facts/templates/*.yaml', {
  query: '?raw',
  import: 'default',
  eager: true,
});

function templateKeys(): string[] {
  return Object.values(templates).flatMap((yaml) =>
    [...yaml.matchAll(/^- key: ([\w.-]+)$/gm)].map(([, key]) => key ?? ''),
  );
}

function templateModules(): string[] {
  return Object.values(templates).flatMap((yaml) =>
    [...yaml.matchAll(/^ {2}module: ([\w-]+)$/gm)].map(([, module]) => module ?? ''),
  );
}

describe('fact presentation', () => {
  it('covers every fact template', () => {
    const keys = templateKeys();
    expect(keys.length).toBeGreaterThanOrEqual(25);
    expect(keys.filter((key) => !(key in PRESENTATIONS))).toEqual([]);
  });

  it('has no presentation for a template that no longer exists', () => {
    const keys = new Set(templateKeys());
    expect(Object.keys(PRESENTATIONS).filter((key) => !keys.has(key))).toEqual([]);
  });

  it('gives every module an accent', () => {
    expect([...new Set(templateModules())].filter((module) => !(module in MODULE_ACCENTS))).toEqual(
      [],
    );
  });

  it.each([
    ['en', { attempts: 2456 }, '2,456'],
    ['ja', { attempts: 2456 }, '2,456'],
    ['en', { attempts: 13822 }, '13,822'],
    ['ja', { attempts: 13822 }, '1.4万'],
  ] as const)('formats integers for %s', (locale, params, expected) => {
    expect(figureFor(locale, { param: 'attempts', format: 'integer' }, params)?.value).toBe(
      expected,
    );
  });

  it('formats shares, years, ranges and classes', () => {
    expect(figureFor('en', { param: 'rate', format: 'percent' }, { rate: 0.686 })?.value).toBe(
      '69%',
    );
    expect(figureFor('ja', { param: 'date', format: 'year' }, { date: '1958-03-17' })?.value).toBe(
      '1958',
    );
    expect(
      figureFor(
        'en',
        { range: ['size_min', 'size_max'], unit: 'm' },
        { size_min: 2800, size_max: 6300 },
      ),
    ).toEqual({ value: '2,800–6,300', unit: 'm' });
    expect(
      figureFor('en', { param: 'flare_class', format: 'text' }, { flare_class: 'M2.3' })?.value,
    ).toBe('M2.3');
  });

  it('omits the figure when its parameter is missing', () => {
    expect(figureFor('en', { param: 'attempts', format: 'integer' }, {})).toBeUndefined();
  });
});
