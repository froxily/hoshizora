import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import type { Locale } from '../i18n/locales';

export function Brand({ locale }: { locale: Locale }) {
  const { t } = useTranslation();
  return (
    <Link
      to={`/${locale}`}
      aria-label={t('brand')}
      className="group flex shrink-0 items-baseline gap-3 whitespace-nowrap"
    >
      <span lang="ja" className="font-display text-xl font-light text-ink">
        星空
      </span>
      <span
        lang="en"
        className="hidden text-xs tracking-label text-ink-muted uppercase min-[400px]:inline transition-colors duration-[var(--hz-duration-fast)] group-hover:text-amber"
      >
        Hoshizora
      </span>
    </Link>
  );
}
