import i18next from 'i18next';
import { initReactI18next } from 'react-i18next';
import { DEFAULT_LOCALE, LOCALES, type Locale } from './locales';
import { DEFAULT_NAMESPACE, resources } from './resources';

export const i18n = i18next.createInstance();

export function initI18n(locale: Locale): void {
  void i18n.use(initReactI18next).init({
    resources,
    lng: locale,
    fallbackLng: DEFAULT_LOCALE,
    supportedLngs: LOCALES,
    defaultNS: DEFAULT_NAMESPACE,
    ns: [DEFAULT_NAMESPACE],
    initAsync: false,
    interpolation: { escapeValue: false },
  });
}
