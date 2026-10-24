import { describe, expect, it } from 'vitest';
import {
  isLocale,
  localeFromPath,
  localizePath,
  matchLocale,
  otherLocale,
  resolvePreferredLocale,
  stripLocale,
} from './locales';

describe('isLocale', () => {
  it.each(['en', 'ja'])('accepts %s', (value) => {
    expect(isLocale(value)).toBe(true);
  });

  it.each(['fr', 'EN', '', null, undefined])('rejects %s', (value) => {
    expect(isLocale(value)).toBe(false);
  });
});

describe('matchLocale', () => {
  it.each([
    ['ja-JP', 'ja'],
    ['JA', 'ja'],
    ['en-GB', 'en'],
    ['de-DE', undefined],
  ])('maps %s to %s', (tag, expected) => {
    expect(matchLocale(tag)).toBe(expected);
  });
});

describe('resolvePreferredLocale', () => {
  it('prefers a stored choice over the browser languages', () => {
    expect(resolvePreferredLocale('en', ['ja-JP'])).toBe('en');
  });

  it('ignores a stored value that is not a supported locale', () => {
    expect(resolvePreferredLocale('fr', ['ja-JP'])).toBe('ja');
  });

  it('uses the first supported browser language', () => {
    expect(resolvePreferredLocale(null, ['de-DE', 'ja-JP', 'en-US'])).toBe('ja');
  });

  it('falls back to English', () => {
    expect(resolvePreferredLocale(null, ['de-DE'])).toBe('en');
    expect(resolvePreferredLocale(null, [])).toBe('en');
  });
});

describe('locale paths', () => {
  it.each([
    ['/', '/ja'],
    ['/en', '/ja'],
    ['/en/launches', '/ja/launches'],
    ['/launches/2026', '/ja/launches/2026'],
    ['/en/launches/', '/ja/launches'],
  ])('localizes %s to %s', (pathname, expected) => {
    expect(localizePath(pathname, 'ja')).toBe(expected);
  });

  it.each([
    ['/ja/launches', '/launches'],
    ['/ja', '/'],
    ['/launches', '/launches'],
  ])('strips the locale from %s', (pathname, expected) => {
    expect(stripLocale(pathname)).toBe(expected);
  });

  it('reads the locale from the first segment only', () => {
    expect(localeFromPath('/ja/launches')).toBe('ja');
    expect(localeFromPath('/launches/ja')).toBeUndefined();
  });

  it('switches between the two locales', () => {
    expect(otherLocale('en')).toBe('ja');
    expect(otherLocale('ja')).toBe('en');
  });
});
