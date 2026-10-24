import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Link, useParams } from 'react-router';
import { ApiError } from '../api/client';
import { agencyQuery, launchCadenceQuery, type Schemas } from '../api/queries';
import { useDocumentTitle } from '../app/useDocumentTitle';
import type { ChartOption } from '../charts/echarts';
import { axisStyle, baseOption } from '../charts/theme';
import { useChartTheme } from '../charts/useChartTheme';
import { ChartFigure } from '../components/ChartFigure';
import { DataRegion } from '../components/DataRegion';
import { DataTable } from '../components/DataTable';
import { LaunchList } from '../components/LaunchTable';
import { ModuleFacts } from '../components/ModuleFacts';
import { Section } from '../components/Section';
import { SourceNote } from '../components/SourceNote';
import { StatTile } from '../components/StatTile';
import { formatNumber } from '../format/format';
import type { Locale } from '../i18n/locales';
import { useLocale } from '../i18n/useLocale';

type Agency = Schemas['AgencyDetail'];
type Year = Schemas['LaunchCadenceYear'];

function percent(locale: Locale, value: number | undefined): string {
  return value === undefined
    ? '—'
    : formatNumber(locale, value, { style: 'percent', maximumFractionDigits: 1 });
}

function continuousYears(recorded: readonly Year[], lastYear: number): Year[] {
  const byYear = new Map(recorded.map((year) => [year.year, year]));
  const first = Math.min(...byYear.keys());
  if (!Number.isFinite(first)) {
    return [];
  }
  return Array.from({ length: lastYear - first + 1 }, (_, index) => first + index).map(
    (year) =>
      byYear.get(year) ?? {
        year,
        attempts: 0,
        successes: 0,
        failures: 0,
        partial_failures: 0,
        scheduled: 0,
        records_url: '',
      },
  );
}

function Cadence({ agencyKey }: { agencyKey: string }) {
  const { t } = useTranslation();
  const locale = useLocale();
  const theme = useChartTheme();
  const query = useQuery(launchCadenceQuery(locale, { group_by: 'provider', key: agencyKey }));
  const lastYear = new Date().getUTCFullYear();
  const years = useMemo(
    () => continuousYears(query.data?.groups[0]?.years ?? [], lastYear),
    [query.data, lastYear],
  );
  const option = useMemo<ChartOption>(() => {
    const axis = axisStyle(theme);
    return {
      ...baseOption(theme),
      tooltip: { ...baseOption(theme).tooltip, trigger: 'axis', axisPointer: { type: 'shadow' } },
      xAxis: {
        type: 'category',
        data: years.map((year) => String(year.year)),
        ...axis,
        splitLine: { show: false },
      },
      yAxis: { type: 'value', minInterval: 1, ...axis },
      series: [
        {
          type: 'bar',
          name: t('common.attempts'),
          data: years.map((year) => year.attempts),
          itemStyle: { color: theme.warm, borderRadius: [3, 3, 0, 0] },
        },
      ],
    };
  }, [theme, years, t]);

  return (
    <DataRegion query={query} minHeight={400}>
      {() =>
        years.length === 0 ? (
          <p className="text-ink-muted">{t('common.none')}</p>
        ) : (
          <ChartFigure<Year>
            title={t('agencies.profile.cadence')}
            description={t('agencies.profile.cadenceDescription')}
            option={option}
            height={280}
            sources={['launch-library']}
            rows={[...years].reverse()}
            rowKey={(year) => String(year.year)}
            columns={[
              { key: 'year', header: t('common.year'), cell: (year) => year.year },
              {
                key: 'attempts',
                header: t('common.attempts'),
                numeric: true,
                cell: (year) => formatNumber(locale, year.attempts),
              },
              {
                key: 'successes',
                header: t('common.successes'),
                numeric: true,
                cell: (year) => formatNumber(locale, year.successes),
              },
              {
                key: 'failures',
                header: t('common.failures'),
                numeric: true,
                cell: (year) => formatNumber(locale, year.failures + year.partial_failures),
              },
            ]}
          />
        )
      }
    </DataRegion>
  );
}

function Profile({ agency }: { agency: Agency }) {
  const { t } = useTranslation();
  const locale = useLocale();
  const objects = agency.catalogued_objects;
  useDocumentTitle(agency.name);

  return (
    <>
      <header className="hz-rise max-w-3xl pt-16 pb-12 sm:pt-24">
        <p className="hz-label mb-6 text-cyan">
          {agency.type !== undefined && (
            <span lang={agency.type.name_lang}>{agency.type.name}</span>
          )}
          {agency.countries.length > 0 &&
            ` · ${agency.countries.map((country) => country.name).join(', ')}`}
        </p>
        <h1
          lang={agency.name_lang}
          className="font-display text-3xl font-light tracking-display text-ink"
        >
          {agency.name}
          {agency.abbrev !== undefined && agency.abbrev !== agency.name && (
            <span className="ml-3 text-2xl text-ink-muted">{agency.abbrev}</span>
          )}
        </h1>
        <p className="mt-6 flex flex-wrap gap-x-6 gap-y-2 text-ink-muted">
          {agency.founding_year !== undefined && (
            <span>
              {t('common.founded')}: {agency.founding_year}
            </span>
          )}
          {agency.programs.length > 0 && (
            <span>{agency.programs.map((program) => program.name).join(', ')}</span>
          )}
          {agency.name_ja_source !== undefined && locale === 'ja' && (
            <a
              href={agency.name_ja_source}
              className="text-amber underline-offset-4 hover:underline"
              rel="noreferrer"
              target="_blank"
            >
              {t('agencies.profile.japaneseName')}
            </a>
          )}
        </p>
      </header>

      <Section id="agency-stats" title={t('agencies.profile.stats')}>
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label={t('common.attempts')}
            value={formatNumber(locale, agency.launches?.attempts ?? 0)}
          />
          <StatTile
            label={t('common.successRate')}
            value={percent(locale, agency.launches?.success_rate)}
            detail={`${t('common.recentRate')}: ${percent(locale, agency.reliability?.recent_success_rate)}`}
          />
          <StatTile
            label={t('agencies.profile.streak')}
            value={
              agency.reliability === undefined
                ? '—'
                : formatNumber(locale, agency.reliability.current_streak)
            }
          />
          <StatTile
            label={t('agencies.profile.longest')}
            value={
              agency.reliability === undefined
                ? '—'
                : formatNumber(locale, agency.reliability.longest_streak)
            }
          />
        </div>
        <div className="mt-6">
          <SourceNote sources={['launch-library']} />
        </div>
      </Section>

      <Section id="agency-facts" title={t('agencies.profile.facts')}>
        <ModuleFacts entityType="organization" entityKey={agency.key} />
      </Section>

      <Section id="agency-cadence" title={t('agencies.profile.cadence')}>
        <Cadence agencyKey={agency.key} />
      </Section>

      {agency.top_vehicles.length > 0 && (
        <Section id="agency-vehicles" title={t('agencies.profile.vehicles')}>
          <DataTable
            caption={t('agencies.profile.vehicles')}
            rows={agency.top_vehicles}
            rowKey={(vehicle) => String(vehicle.id)}
            columns={[
              {
                key: 'name',
                header: t('common.name'),
                cell: (vehicle) => <span lang={vehicle.name_lang}>{vehicle.name}</span>,
              },
              {
                key: 'attempts',
                header: t('common.attempts'),
                numeric: true,
                cell: (vehicle) => formatNumber(locale, vehicle.attempts),
              },
              {
                key: 'successes',
                header: t('common.successes'),
                numeric: true,
                cell: (vehicle) => formatNumber(locale, vehicle.successes),
              },
            ]}
          />
        </Section>
      )}

      <Section id="agency-launches" title={t('agencies.profile.recent')}>
        <div className="flex flex-col gap-12">
          {agency.next_launch !== undefined && (
            <div className="flex flex-col gap-4">
              <h3 className="font-display text-xl font-light text-ink">
                {t('agencies.profile.next')}
              </h3>
              <LaunchList title={t('agencies.profile.next')} launches={[agency.next_launch]} />
            </div>
          )}
          <LaunchList title={t('agencies.profile.recent')} launches={agency.recent_launches} />
        </div>
      </Section>

      {objects !== undefined && (
        <Section id="agency-objects" title={t('agencies.profile.objects')}>
          <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile
              label={t('agencies.profile.inOrbit')}
              value={formatNumber(locale, objects.in_earth_orbit)}
            />
            <StatTile
              label={t('agencies.profile.payloads')}
              value={formatNumber(locale, objects.payloads_in_earth_orbit)}
            />
            <StatTile
              label={t('agencies.profile.decayed')}
              value={formatNumber(locale, objects.decayed)}
            />
            <StatTile
              label={t('agencies.profile.beyond')}
              value={formatNumber(locale, objects.beyond_earth)}
            />
          </div>
          <div className="mt-6">
            <SourceNote sources={['celestrak']} />
          </div>
        </Section>
      )}
    </>
  );
}

export function AgencyPage() {
  const { t } = useTranslation();
  const locale = useLocale();
  const { key = '' } = useParams();
  const query = useQuery(agencyQuery(locale, key));
  const missing = query.error instanceof ApiError && query.error.status === 404;

  return (
    <div className="mx-auto max-w-7xl px-gutter pt-16">
      <Link
        to={`/${locale}/agencies`}
        className="mt-8 inline-block text-sm text-amber underline-offset-4 hover:underline"
      >
        ← {t('agencies.profile.back')}
      </Link>
      {missing ? (
        <p className="py-section text-lg text-ink-muted">{t('agencies.notFound')}</p>
      ) : (
        <DataRegion query={query} minHeight={480}>
          {(agency) => <Profile agency={agency} />}
        </DataRegion>
      )}
    </div>
  );
}
