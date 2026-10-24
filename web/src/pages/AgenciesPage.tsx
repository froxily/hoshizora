import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Link } from 'react-router';
import { agenciesQuery, type Schemas } from '../api/queries';
import { useDocumentTitle } from '../app/useDocumentTitle';
import { DataRegion } from '../components/DataRegion';
import { PageLayout } from '../components/PageLayout';
import { SourceNote } from '../components/SourceNote';
import { formatNumber } from '../format/format';
import { useLocale } from '../i18n/useLocale';

const TYPES = ['agency', 'company', 'military', 'international'] as const;

type AgencyType = (typeof TYPES)[number];
type Agency = Schemas['AgencySummary'];

function AgencyCard({ agency }: { agency: Agency }) {
  const { t } = useTranslation();
  const locale = useLocale();
  const rate = agency.launches?.success_rate;

  return (
    <Link
      to={`/${locale}/agencies/${agency.key}`}
      className="group flex flex-col gap-3 border-t border-hairline-strong pt-5 transition-colors duration-[var(--hz-duration-fast)] hover:border-amber"
    >
      <span className="hz-label">
        {agency.type !== undefined && <span lang={agency.type.name_lang}>{agency.type.name}</span>}
        {agency.countries.length > 0 &&
          ` · ${agency.countries.map((country) => country.name).join(', ')}`}
      </span>
      <span
        lang={agency.name_lang}
        className="font-display text-xl font-light text-ink group-hover:text-amber"
      >
        {agency.name}
        {agency.abbrev !== undefined && agency.abbrev !== agency.name && (
          <span className="ml-2 text-base text-ink-muted">{agency.abbrev}</span>
        )}
      </span>
      <span className="flex flex-wrap gap-x-5 gap-y-1 text-sm text-ink-muted tabular-nums">
        <span>
          {t('agencies.launches', { value: formatNumber(locale, agency.launches?.attempts ?? 0) })}
        </span>
        {rate !== undefined && (
          <span>
            {t('agencies.rate', {
              rate: formatNumber(locale, rate, { style: 'percent', maximumFractionDigits: 1 }),
            })}
          </span>
        )}
      </span>
    </Link>
  );
}

export function AgenciesPage() {
  const { t } = useTranslation();
  const locale = useLocale();
  const [type, setType] = useState<AgencyType | null>(null);
  const query = useQuery(
    agenciesQuery(locale, {
      has_launches: true,
      sort: '-launches',
      size: 60,
      ...(type === null ? {} : { type }),
    }),
  );
  useDocumentTitle(t('pages.agencies.title'));

  return (
    <PageLayout title={t('pages.agencies.title')} lede={t('pages.agencies.lede')}>
      <div className="flex flex-col gap-10 pb-section">
        <div role="group" aria-label={t('agencies.filter')} className="flex flex-wrap gap-2">
          {[null, ...TYPES].map((option) => (
            <button
              key={option ?? 'all'}
              type="button"
              aria-pressed={type === option}
              onClick={() => {
                setType(option);
              }}
              className={`rounded-pill border px-4 py-1.5 text-sm transition-colors duration-[var(--hz-duration-fast)] ${type === option ? 'border-amber bg-amber-soft text-ink' : 'border-hairline text-ink-muted hover:border-hairline-strong hover:text-ink'}`}
            >
              {option === null ? t('common.all') : t(`agencies.types.${option}`)}
            </button>
          ))}
        </div>
        <DataRegion query={query} minHeight={480}>
          {(page) =>
            page.items.length === 0 ? (
              <p className="text-ink-muted">{t('common.none')}</p>
            ) : (
              <div className="grid gap-x-10 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
                {page.items.map((agency) => (
                  <AgencyCard key={agency.key} agency={agency} />
                ))}
              </div>
            )
          }
        </DataRegion>
        <SourceNote sources={['launch-library']} />
      </div>
    </PageLayout>
  );
}
