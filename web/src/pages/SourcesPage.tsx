import { useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { sourcesQuery, type Schemas } from '../api/queries';
import { useDocumentTitle } from '../app/useDocumentTitle';
import credits from '../assets/credits.json';
import { DataRegion } from '../components/DataRegion';
import { PageLayout } from '../components/PageLayout';
import { Section } from '../components/Section';
import { formatDateTime } from '../format/format';
import { useLocale } from '../i18n/useLocale';

type Source = Schemas['SourceView'];

const LEVEL_TONE: Record<string, string> = {
  ok: 'bg-positive',
  warning: 'bg-amber',
  blocking: 'bg-negative',
};

const FRESHNESS_TONE: Record<string, string> = {
  fresh: 'bg-positive',
  stale: 'bg-amber',
};

function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <dt className="hz-label">{label}</dt>
      <dd className="text-sm text-ink">{children}</dd>
    </div>
  );
}

function Status({ tone, name, lang }: { tone: string | undefined; name: string; lang: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className={`size-2 rounded-full ${tone ?? 'bg-ink-faint'}`} aria-hidden />
      <span lang={lang}>{name}</span>
    </span>
  );
}

function SourceCard({ source }: { source: Source }) {
  const { t } = useTranslation();
  const locale = useLocale();
  const fetched = source.status.last_succeeded_at ?? source.status.last_fetched_at;

  return (
    <article className="flex flex-col gap-6 border-t border-hairline-strong pt-6">
      <div className="flex flex-col gap-2">
        <h3 className="font-display text-2xl font-light text-ink">{source.name}</h3>
        <p className="max-w-3xl text-ink-muted">{source.description}</p>
        <a
          href={source.homepage_url}
          rel="noreferrer"
          target="_blank"
          className="w-fit text-sm text-amber underline-offset-4 hover:underline"
        >
          {t('sources.visit')}
        </a>
      </div>
      <dl className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <Detail label={t('sources.license')}>
          {source.license_url === undefined ? (
            source.license
          ) : (
            <a
              href={source.license_url}
              rel="noreferrer"
              target="_blank"
              className="underline-offset-4 hover:underline"
            >
              {source.license}
            </a>
          )}
        </Detail>
        <Detail label={t('sources.credit')}>{source.credit}</Detail>
        <Detail label={t('sources.cadence')}>{source.cadence}</Detail>
        <Detail label={t('sources.lastFetched')}>
          {fetched === undefined ? '—' : formatDateTime(locale, fetched)}
        </Detail>
        <Detail label={t('sources.freshness')}>
          <Status
            tone={FRESHNESS_TONE[source.status.freshness.code]}
            name={source.status.freshness.name}
            lang={source.status.freshness.name_lang}
          />
        </Detail>
        <Detail label={t('sources.quality')}>
          <Status
            tone={LEVEL_TONE[source.quality.level.code]}
            name={source.quality.level.name}
            lang={source.quality.level.name_lang}
          />
        </Detail>
      </dl>
    </article>
  );
}

export function SourcesPage() {
  const { t } = useTranslation();
  const locale = useLocale();
  const query = useQuery(sourcesQuery(locale));
  useDocumentTitle(t('pages.sources.title'));

  return (
    <PageLayout title={t('pages.sources.title')} lede={t('pages.sources.lede')}>
      <Section id="sources-list" title={t('sources.data')}>
        <DataRegion query={query} minHeight={600}>
          {(page) => (
            <div className="flex flex-col gap-14">
              {page.items.map((source) => (
                <SourceCard key={source.slug} source={source} />
              ))}
            </div>
          )}
        </DataRegion>
      </Section>
      <Section id="sources-gaps" title={t('sources.gaps')}>
        <p className="max-w-3xl text-ink-muted">{t('sources.gapsBody')}</p>
      </Section>
      <Section id="sources-fonts" title={t('sources.fonts')} lede={t('sources.fontsLede')}>
        <div className="grid gap-10 sm:grid-cols-2">
          {credits.map((credit) => (
            <article
              key={credit.name}
              className="flex flex-col gap-2 border-t border-hairline-strong pt-5"
            >
              <h3 className="font-display text-xl font-light text-ink">{credit.name}</h3>
              <p className="text-sm text-ink-muted">{credit.credit}</p>
              <p className="flex flex-wrap gap-x-5 text-sm">
                <a
                  href={credit.license_url}
                  rel="noreferrer"
                  target="_blank"
                  className="text-amber underline-offset-4 hover:underline"
                >
                  {credit.license}
                </a>
                <a
                  href={credit.source_url}
                  rel="noreferrer"
                  target="_blank"
                  className="text-amber underline-offset-4 hover:underline"
                >
                  {t('sources.visit')}
                </a>
              </p>
            </article>
          ))}
        </div>
      </Section>
    </PageLayout>
  );
}
