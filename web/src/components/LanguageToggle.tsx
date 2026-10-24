import { useTranslation } from 'react-i18next';
import { Link, useLocation } from 'react-router';
import { localizePath, otherLocale, type Locale } from '../i18n/locales';
import { storeLocale } from '../i18n/preference';

export function LanguageToggle({ current }: { current: Locale }) {
  const { t } = useTranslation();
  const { pathname, search, hash } = useLocation();
  const target = otherLocale(current);

  return (
    <Link
      to={{ pathname: localizePath(pathname, target), search, hash }}
      hrefLang={target}
      aria-label={t('language.switchTo', { language: t(`language.name.${target}`) })}
      onClick={() => storeLocale(target)}
      className="rounded-full border whitespace-nowrap border-hairline px-4 py-1.5 text-sm text-ink-muted transition-colors duration-500 hover:border-amber hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-amber motion-reduce:transition-none"
    >
      <span lang={target}>{t(`language.endonym.${target}`)}</span>
    </Link>
  );
}
