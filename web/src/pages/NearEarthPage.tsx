import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  closeApproachesQuery,
  closeApproachMonthlyQuery,
  impactRisksQuery,
  type Schemas,
} from '../api/queries';
import { useDocumentTitle } from '../app/useDocumentTitle';
import type { ChartOption } from '../charts/echarts';
import { axisStyle, baseOption } from '../charts/theme';
import { useChartTheme } from '../charts/useChartTheme';
import { ChartFigure } from '../components/ChartFigure';
import { DataRegion } from '../components/DataRegion';
import { DataTable } from '../components/DataTable';
import { ModuleFacts } from '../components/ModuleFacts';
import { PageLayout } from '../components/PageLayout';
import { Section } from '../components/Section';
import { SourceNote } from '../components/SourceNote';
import { formatDate, formatNumber } from '../format/format';
import type { Locale } from '../i18n/locales';
import { useLocale } from '../i18n/useLocale';

type Approach = Schemas['CloseApproach'];
type Month = Schemas['CloseApproachMonth'];
type Risk = Schemas['ImpactRisk'];

const DAY_MS = 86_400_000;
const UPCOMING_DAYS = 60;

function isoDate(offsetDays: number, now: number = Date.now()): string {
  return new Date(Math.floor(now / DAY_MS) * DAY_MS + offsetDays * DAY_MS)
    .toISOString()
    .slice(0, 10);
}

function monthStart(offsetMonths: number): string {
  const now = new Date();
  return new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + offsetMonths, 1))
    .toISOString()
    .slice(0, 10);
}

function meters(locale: Locale, km: number): string {
  return formatNumber(locale, km * 1_000, { maximumSignificantDigits: 2 });
}

function sizeRange(locale: Locale, approach: Approach): string {
  const { estimated_min_km: min, estimated_max_km: max } = approach.size;
  return min === undefined || max === undefined
    ? '—'
    : `${meters(locale, min)}–${meters(locale, max)} m`;
}

function middleSizeMeters(approach: Approach): number | undefined {
  const { estimated_min_km: min, estimated_max_km: max } = approach.size;
  return min === undefined || max === undefined ? undefined : Math.sqrt(min * max) * 1_000;
}

function monthLabel(locale: Locale, month: string): string {
  return new Intl.DateTimeFormat(locale === 'ja' ? 'ja-JP' : 'en-US', {
    year: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  }).format(new Date(month));
}

function Monthly() {
  const { t } = useTranslation();
  const locale = useLocale();
  const theme = useChartTheme();
  const query = useQuery(
    closeApproachMonthlyQuery(locale, { from: monthStart(-12), to: monthStart(13) }),
  );
  const months = useMemo(() => query.data?.items ?? [], [query.data]);
  const option = useMemo<ChartOption>(() => {
    const axis = axisStyle(theme);
    const bar = (name: string, color: string, values: (month: Month) => number) => ({
      type: 'bar' as const,
      name,
      stack: 'approaches',
      color,
      barWidth: '55%',
      data: months.map((month) => ({
        value: values(month),
        itemStyle: { color, opacity: month.predicted ? 0.45 : 1 },
      })),
    });
    return {
      ...baseOption(theme),
      tooltip: { ...baseOption(theme).tooltip, trigger: 'axis', axisPointer: { type: 'shadow' } },
      xAxis: {
        type: 'category',
        data: months.map((month) => monthLabel(locale, month.month)),
        ...axis,
        splitLine: { show: false },
      },
      yAxis: { type: 'value', ...axis },
      series: [
        bar(t('nearEarth.closerThanMoon'), theme.warm, (month) => month.within_lunar_distance),
        {
          ...bar(
            t('nearEarth.approaches'),
            theme.cool,
            (month) => month.approaches - month.within_lunar_distance,
          ),
          itemStyle: { borderRadius: [4, 4, 0, 0] },
        },
      ],
    };
  }, [theme, months, locale, t]);

  return (
    <DataRegion query={query} minHeight={460}>
      {(data) => (
        <ChartFigure
          legend={[
            { label: t('nearEarth.closerThanMoon'), color: theme.warm },
            { label: t('nearEarth.approaches'), color: theme.cool },
          ]}
          title={t('nearEarth.monthly.title')}
          description={t('nearEarth.monthly.description')}
          option={option}
          height={340}
          sources={['jpl']}
          rows={data.items}
          rowKey={(month) => month.month}
          columns={[
            {
              key: 'month',
              header: t('common.month'),
              cell: (month) =>
                `${monthLabel(locale, month.month)}${month.predicted ? ` (${t('nearEarth.predicted')})` : ''}`,
            },
            {
              key: 'approaches',
              header: t('nearEarth.approaches'),
              numeric: true,
              cell: (month) => formatNumber(locale, month.approaches),
            },
            {
              key: 'moon',
              header: t('nearEarth.closerThanMoon'),
              numeric: true,
              cell: (month) => formatNumber(locale, month.within_lunar_distance),
            },
            {
              key: 'closest',
              header: t('nearEarth.closest'),
              cell: (month) =>
                `${month.closest_designation} · ${formatNumber(locale, month.closest_dist_ld, { maximumFractionDigits: 2 })} ${t('units.ld')}`,
            },
          ]}
        />
      )}
    </DataRegion>
  );
}

function SizeDistance() {
  const { t } = useTranslation();
  const locale = useLocale();
  const theme = useChartTheme();
  const query = useQuery(
    closeApproachesQuery(locale, {
      from: isoDate(0),
      to: isoDate(UPCOMING_DAYS),
      sort: 'distance',
      size: 100,
    }),
  );
  const approaches = useMemo(() => query.data?.items ?? [], [query.data]);
  const option = useMemo<ChartOption>(() => {
    const axis = axisStyle(theme);
    const points = approaches.flatMap((approach) => {
      const size = middleSizeMeters(approach);
      return size === undefined ? [] : [{ value: [approach.dist_ld, size], approach }];
    });
    return {
      ...baseOption(theme),
      grid: { left: 8, right: 24, top: 24, bottom: 32, containLabel: true },
      tooltip: {
        ...baseOption(theme).tooltip,
        trigger: 'item',
        formatter: (item: { data: { approach: Approach } }) => {
          const approach = item.data.approach;
          return [
            `<strong>${approach.fullname?.trim() ?? approach.designation}</strong>`,
            formatDate(locale, approach.approach_utc ?? approach.approach_tdb),
            `${t('nearEarth.distance')}: ${formatNumber(locale, approach.dist_ld, { maximumFractionDigits: 2 })} ${t('units.ld')}`,
            `${t('nearEarth.diameter')}: ${sizeRange(locale, approach)}`,
          ].join('<br/>');
        },
      },
      xAxis: {
        type: 'log',
        name: t('units.ldLong'),
        nameLocation: 'middle',
        nameGap: 28,
        ...axis,
      },
      yAxis: { type: 'log', name: `${t('nearEarth.diameter')} (m)`, ...axis },
      series: [
        {
          type: 'scatter',
          name: t('nearEarth.approaches'),
          data: points,
          symbolSize: 9,
          itemStyle: {
            color: theme.cool,
            opacity: 0.85,
            borderColor: theme.canvas,
            borderWidth: 1,
          },
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { color: theme.warm, type: 'dashed' },
            label: { formatter: t('nearEarth.moonLine'), color: theme.ink },
            data: [{ xAxis: 1 }],
          },
        },
      ],
    };
  }, [theme, approaches, locale, t]);

  return (
    <DataRegion query={query} minHeight={500}>
      {(data) => (
        <ChartFigure
          title={t('nearEarth.sizeDistance.title')}
          description={t('nearEarth.sizeDistance.description')}
          option={option}
          height={380}
          sources={['jpl']}
          rows={data.items}
          rowKey={(approach) => `${approach.designation}|${approach.approach_tdb}`}
          columns={[
            {
              key: 'object',
              header: t('nearEarth.object'),
              cell: (approach) => approach.fullname?.trim() ?? approach.designation,
            },
            {
              key: 'date',
              header: t('common.date'),
              cell: (approach) =>
                formatDate(locale, approach.approach_utc ?? approach.approach_tdb),
            },
            {
              key: 'distance',
              header: `${t('nearEarth.distance')} (${t('units.ld')})`,
              numeric: true,
              cell: (approach) =>
                formatNumber(locale, approach.dist_ld, { maximumFractionDigits: 2 }),
            },
            {
              key: 'size',
              header: t('nearEarth.diameter'),
              numeric: true,
              cell: (approach) => sizeRange(locale, approach),
            },
            {
              key: 'speed',
              header: `${t('nearEarth.speed')} (km/s)`,
              numeric: true,
              cell: (approach) =>
                approach.v_rel_kms === undefined
                  ? '—'
                  : formatNumber(locale, approach.v_rel_kms, { maximumFractionDigits: 1 }),
            },
          ]}
        />
      )}
    </DataRegion>
  );
}

function probability(
  locale: Locale,
  t: (key: 'nearEarth.oneIn', options: { count: string }) => string,
  value: number,
): string {
  if (value <= 0) {
    return '—';
  }
  return t('nearEarth.oneIn', {
    count: formatNumber(locale, 1 / value, { maximumSignificantDigits: 2 }),
  });
}

function Sentry() {
  const { t } = useTranslation();
  const locale = useLocale();
  const query = useQuery(impactRisksQuery(locale, { sort: '-palermo', size: 10 }));

  return (
    <DataRegion query={query} minHeight={420}>
      {(page) => (
        <div className="flex flex-col gap-4">
          <DataTable<Risk>
            caption={t('nearEarth.sentry.title')}
            rows={page.items}
            rowKey={(risk) => risk.designation}
            columns={[
              {
                key: 'object',
                header: t('nearEarth.object'),
                cell: (risk) => risk.fullname?.trim() ?? risk.designation,
              },
              {
                key: 'years',
                header: t('nearEarth.years'),
                numeric: true,
                cell: (risk) =>
                  risk.impact_year_first === undefined
                    ? '—'
                    : risk.impact_year_first === risk.impact_year_last
                      ? String(risk.impact_year_first)
                      : `${String(risk.impact_year_first)}–${String(risk.impact_year_last ?? '')}`,
              },
              {
                key: 'probability',
                header: t('nearEarth.probability'),
                numeric: true,
                cell: (risk) =>
                  risk.impact_probability === undefined
                    ? '—'
                    : probability(locale, t, risk.impact_probability),
              },
              {
                key: 'palermo',
                header: t('nearEarth.palermo'),
                numeric: true,
                cell: (risk) =>
                  risk.palermo_cumulative === undefined
                    ? '—'
                    : formatNumber(locale, risk.palermo_cumulative, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      }),
              },
              {
                key: 'torino',
                header: t('nearEarth.torino'),
                cell: (risk) =>
                  risk.torino === undefined ? (
                    '—'
                  ) : (
                    <span lang={risk.torino.name_lang}>{risk.torino.name}</span>
                  ),
              },
              {
                key: 'size',
                header: `${t('nearEarth.diameter')} (m)`,
                numeric: true,
                cell: (risk) =>
                  risk.sentry_diameter_km === undefined
                    ? '—'
                    : meters(locale, risk.sentry_diameter_km),
              },
            ]}
          />
          <p className="max-w-3xl text-sm text-ink-muted">{t('nearEarth.sentry.palermoNote')}</p>
          <SourceNote sources={['jpl']} />
        </div>
      )}
    </DataRegion>
  );
}

export function NearEarthPage() {
  const { t } = useTranslation();
  useDocumentTitle(t('pages.nearEarth.title'));

  return (
    <PageLayout title={t('pages.nearEarth.title')} lede={t('pages.nearEarth.lede')}>
      <Section id="near-earth-facts" title={t('nearEarth.facts')}>
        <ModuleFacts module="near-earth" />
      </Section>
      <Section
        id="near-earth-monthly"
        title={t('nearEarth.monthly.title')}
        lede={t('nearEarth.monthly.lede')}
      >
        <Monthly />
      </Section>
      <Section
        id="near-earth-size"
        title={t('nearEarth.sizeDistance.title')}
        lede={t('nearEarth.sizeDistance.lede')}
      >
        <SizeDistance />
      </Section>
      <Section
        id="near-earth-sentry"
        title={t('nearEarth.sentry.title')}
        lede={t('nearEarth.sentry.lede')}
      >
        <Sentry />
      </Section>
    </PageLayout>
  );
}
