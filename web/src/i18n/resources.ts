import enCommon from '../locales/en/common.json';
import jaCommon from '../locales/ja/common.json';
import type { Locale } from './locales';

export const DEFAULT_NAMESPACE = 'common';

export const resources = {
  en: { common: enCommon },
  ja: { common: jaCommon },
} as const satisfies Record<Locale, Record<typeof DEFAULT_NAMESPACE, unknown>>;
