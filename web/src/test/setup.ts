import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';
import { initI18n } from '../i18n/i18n';
import { DEFAULT_LOCALE } from '../i18n/locales';

beforeEach(() => {
  initI18n(DEFAULT_LOCALE);
  vi.stubGlobal('fetch', () => new Promise<Response>(() => undefined));
});

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  document.documentElement.lang = '';
  document.title = '';
  document.head.replaceChildren();
});
