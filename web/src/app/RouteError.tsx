import { useTranslation } from 'react-i18next';
import { HeroPoster } from '../hero/HeroPoster';
import { localeFromPath } from '../i18n/locales';

export function RouteError() {
  const { t } = useTranslation();
  const home = `/${localeFromPath(window.location.pathname) ?? ''}`;

  return (
    <main className="relative isolate flex min-h-dvh items-center">
      <div className="absolute inset-0 -z-10" aria-hidden>
        <HeroPoster />
      </div>
      <section className="mx-auto w-full max-w-7xl px-gutter" role="alert">
        <h1 className="max-w-3xl font-display text-3xl font-light text-ink">{t('crash.title')}</h1>
        <p className="mt-6 max-w-xl text-lg text-ink-muted">{t('crash.body')}</p>
        <div className="mt-10 flex flex-wrap gap-4">
          <button
            type="button"
            onClick={() => {
              window.location.reload();
            }}
            className="rounded-pill border border-amber px-5 py-2 text-sm text-ink hover:bg-amber-soft"
          >
            {t('crash.reload')}
          </button>
          <a
            href={home}
            className="rounded-pill border border-hairline px-5 py-2 text-sm text-ink-muted hover:text-ink"
          >
            {t('crash.home')}
          </a>
        </div>
      </section>
    </main>
  );
}
