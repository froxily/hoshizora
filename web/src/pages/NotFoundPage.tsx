import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router';
import { useDocumentTitle } from '../app/useDocumentTitle';

export function NotFoundPage() {
  const { t } = useTranslation();
  const { locale = '' } = useParams();
  useDocumentTitle(t('notFound.title'));

  return (
    <section className="mx-auto max-w-7xl px-gutter pt-40">
      <h1 className="mb-6 font-display text-3xl font-light text-ink">{t('notFound.title')}</h1>
      <p className="mb-10 text-lg text-ink-muted">{t('notFound.body')}</p>
      <Link
        to={`/${locale}`}
        className="text-amber underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-amber"
      >
        {t('notFound.home')}
      </Link>
    </section>
  );
}
