import { useLayoutEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Outlet, useLocation, useParams } from 'react-router';
import { SiteFooter } from '../components/SiteFooter';
import { SiteHeader } from '../components/SiteHeader';
import { isLocale, LOCALES, localizePath, stripLocale, type Locale } from '../i18n/locales';
import { LocaleRedirect } from './LocaleRedirect';

const MAIN_ID = 'main';

function absoluteUrl(pathname: string): string {
  return new URL(pathname, window.location.origin).href;
}

function AlternateLinks({ pathname }: { pathname: string }) {
  return (
    <>
      {LOCALES.map((locale) => (
        <link
          key={locale}
          rel="alternate"
          hrefLang={locale}
          href={absoluteUrl(localizePath(pathname, locale))}
        />
      ))}
      <link rel="alternate" hrefLang="x-default" href={absoluteUrl(stripLocale(pathname))} />
    </>
  );
}

function LocalizedShell({ locale }: { locale: Locale }) {
  const { t, i18n } = useTranslation();
  const { pathname } = useLocation();

  useLayoutEffect(() => {
    void i18n.changeLanguage(locale);
    document.documentElement.lang = locale;
  }, [i18n, locale]);

  return (
    <>
      <meta name="description" content={t('meta.description')} />
      <AlternateLinks pathname={pathname} />
      <a
        href={`#${MAIN_ID}`}
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded focus:bg-canvas focus:px-4 focus:py-2 focus:text-ink focus:outline focus:outline-amber"
      >
        {t('a11y.skipToContent')}
      </a>
      <SiteHeader locale={locale} />
      <main id={MAIN_ID} tabIndex={-1} className="min-h-dvh outline-none">
        <Outlet />
      </main>
      <SiteFooter locale={locale} />
    </>
  );
}

export function LocaleLayout() {
  const { locale } = useParams();
  return isLocale(locale) ? <LocalizedShell locale={locale} /> : <LocaleRedirect />;
}
