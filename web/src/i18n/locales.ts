export const LOCALES = ['en', 'ja'] as const;

export type Locale = (typeof LOCALES)[number];

export const DEFAULT_LOCALE: Locale = 'en';

export function isLocale(value: string | null | undefined): value is Locale {
  return LOCALES.some((locale) => locale === value);
}

export function matchLocale(languageTag: string): Locale | undefined {
  const primary = languageTag.trim().toLowerCase().split('-')[0];
  return LOCALES.find((locale) => locale === primary);
}

export function resolvePreferredLocale(
  stored: string | null,
  browserLanguages: readonly string[],
): Locale {
  if (isLocale(stored)) {
    return stored;
  }
  return browserLanguages.map(matchLocale).find(isLocale) ?? DEFAULT_LOCALE;
}

function pathSegments(pathname: string): string[] {
  return pathname.split('/').filter((segment) => segment !== '');
}

export function localeFromPath(pathname: string): Locale | undefined {
  const [first] = pathSegments(pathname);
  return isLocale(first) ? first : undefined;
}

export function stripLocale(pathname: string): string {
  const segments = pathSegments(pathname);
  const rest = isLocale(segments[0]) ? segments.slice(1) : segments;
  return `/${rest.join('/')}`;
}

export function localizePath(pathname: string, locale: Locale): string {
  const rest = stripLocale(pathname);
  return rest === '/' ? `/${locale}` : `/${locale}${rest}`;
}

export function otherLocale(locale: Locale): Locale {
  return LOCALES.find((candidate) => candidate !== locale) ?? DEFAULT_LOCALE;
}
