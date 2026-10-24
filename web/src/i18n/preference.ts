import { resolvePreferredLocale, type Locale } from './locales';

export const LOCALE_STORAGE_KEY = 'hoshizora.locale';

export function readStoredLocale(): string | null {
  try {
    return window.localStorage.getItem(LOCALE_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function storeLocale(locale: Locale): boolean {
  try {
    window.localStorage.setItem(LOCALE_STORAGE_KEY, locale);
    return true;
  } catch {
    return false;
  }
}

export function preferredLocale(): Locale {
  return resolvePreferredLocale(readStoredLocale(), navigator.languages);
}
