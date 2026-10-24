import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import type { Locale } from '../i18n/locales';
import { Brand } from './Brand';

export function SiteFooter({ locale }: { locale: Locale }) {
  const { t } = useTranslation();
  return (
    <footer className="mt-section border-t border-hairline">
      <div className="mx-auto grid max-w-7xl gap-8 px-gutter py-12 sm:grid-cols-[auto_1fr_auto] sm:items-start">
        <Brand locale={locale} />
        <div className="max-w-xl text-sm text-ink-muted">
          <p>{t('footer.data')}</p>
          <p className="mt-2">{t('footer.trace')}</p>
        </div>
        <Link
          to={`/${locale}/sources`}
          className="text-sm text-amber underline-offset-4 hover:underline"
        >
          {t('footer.credits')}
        </Link>
      </div>
    </footer>
  );
}
