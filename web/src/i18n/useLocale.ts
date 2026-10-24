import { useParams } from 'react-router';
import { DEFAULT_LOCALE, isLocale, type Locale } from './locales';

export function useLocale(): Locale {
  const { locale } = useParams();
  return isLocale(locale) ? locale : DEFAULT_LOCALE;
}
