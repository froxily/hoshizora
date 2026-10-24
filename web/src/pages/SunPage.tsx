import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  auroraQuery,
  flaresQuery,
  hoursAgo,
  kpQuery,
  solarWindQuery,
  spaceWeatherNowQuery,
  type Schemas,
} from '../api/queries';
import { useDocumentTitle } from '../app/useDocumentTitle';
import { AuroraMap } from '../aurora/AuroraMap';
import { chanceAt, PLACES, type Hemisphere } from '../aurora/projection';
import type { ChartOption } from '../charts/echarts';
import { axisStyle, baseOption, type ChartTheme } from '../charts/theme';
import { useChartTheme } from '../charts/useChartTheme';
import { ChartFigure } from '../components/ChartFigure';
import { DataRegion } from '../components/DataRegion';
import { DataTable } from '../components/DataTable';
import { ModuleFacts } from '../components/ModuleFacts';
import { PageLayout } from '../components/PageLayout';
import { Section } from '../components/Section';
import { SourceNote } from '../components/SourceNote';
import { StatTile } from '../components/StatTile';
import { formatDateTime, formatNumber } from '../format/format';
import type { Locale } from '../i18n/locales';
import { useLocale } from '../i18n/useLocale';

const WEEK_HOURS = 168;
const STORM_KP = 5;
const FLARE_CLASSES = ['A', 'B', 'C', 'M', 'X'] as const;

type Flare = Schemas['Flare'];
type KpReading = Schemas['KpReading'];
type WindPoint = Schemas['SolarWindPoint'];
type Aurora = Schemas['Aurora'];

function decimal(locale: Locale, value: number, digits = 1): string {
  return formatNumber(locale, value, { maximumFractionDigits: digits });
}

function timeAxis(theme: ChartTheme, locale: Locale) {
  const axis = axisStyle(theme);
  return {
    type: 'time' as const,
    ...axis,
    splitLine: { show: false },
    axisLabel: {
      ...axis.axisLabel,
      hideOverlap: true,
      formatter: (value: number) =>
        new Intl.DateTimeFormat(locale === 'ja' ? 'ja-JP' : 'en-US', {
          month: 'short',
          day: 'numeric',
        }).format(new Date(value)),
    },
  };
}

function Now() {
  const { t } = useTranslation();
  const locale = useLocale();
  const query = useQuery(spaceWeatherNowQuery(locale));

  return (
    <DataRegion
      query={query}
      placeholderClassName="min-h-[700px] sm:min-h-[340px] lg:min-h-[160px]"
    >
      {(now) => (
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile
            label={t('sun.kpNow')}
            value={now.kp === undefined ? '—' : decimal(locale, now.kp.kp, 2)}
            unit={t('units.kp')}
            detail={now.kp?.g_scale.name}
            note={
              <SourceNote
                sources={['swpc']}
                {...(now.kp === undefined ? {} : { asOf: now.kp.observed_at })}
              />
            }
          />
          <StatTile
            label={t('sun.windSpeed')}
            value={
              now.solar_wind?.speed_kms === undefined
                ? '—'
                : formatNumber(locale, Math.round(now.solar_wind.speed_kms))
            }
            unit={t('units.kms')}
            note={
              <SourceNote
                sources={['swpc']}
                {...(now.solar_wind === undefined ? {} : { asOf: now.solar_wind.observed_at })}
              />
            }
          />
          <StatTile
            label={t('sun.bz')}
            value={
              now.solar_wind?.bz_gsm_nt === undefined
                ? '—'
                : decimal(locale, now.solar_wind.bz_gsm_nt)
            }
            unit="nT"
            note={
              <SourceNote
                sources={['swpc']}
                {...(now.solar_wind === undefined ? {} : { asOf: now.solar_wind.observed_at })}
              />
            }
          />
          <StatTile
            label={t('sun.flare24h')}
            value={now.strongest_flare_last_day?.xray_class ?? '—'}
            detail={
              now.flares_last_day > 0
                ? t('sun.flareCount', { count: now.flares_last_day })
                : t('sun.noFlare')
            }
            note={<SourceNote sources={['swpc']} asOf={now.as_of} />}
          />
        </div>
      )}
    </DataRegion>
  );
}

function KpChart() {
  const { t } = useTranslation();
  const locale = useLocale();
  const theme = useChartTheme();
  const query = useQuery(kpQuery(locale, { from: hoursAgo(WEEK_HOURS) }));
  const readings = useMemo(() => query.data?.items ?? [], [query.data]);
  const option = useMemo<ChartOption>(() => {
    const axis = axisStyle(theme);
    return {
      ...baseOption(theme),
      tooltip: {
        ...baseOption(theme).tooltip,
        trigger: 'axis',
        valueFormatter: (value: number) => decimal(locale, value, 2),
      },
      grid: { ...baseOption(theme).grid, right: 88 },
      xAxis: timeAxis(theme, locale),
      yAxis: { type: 'value', min: 0, max: 9, interval: 1, ...axis },
      series: [
        {
          type: 'bar',
          name: t('units.kp'),
          barWidth: '60%',
          data: readings.map((reading) => ({
            value: [reading.observed_at, reading.kp],
            itemStyle: {
              color: reading.kp >= STORM_KP ? theme.warm : theme.cool,
              borderRadius: [3, 3, 0, 0],
            },
          })),
          markLine: {
            silent: true,
            symbol: 'none',
            lineStyle: { color: theme.warm, type: 'dashed' },
            label: { formatter: t('scale.storm'), color: theme.ink, position: 'end' },
            data: [{ yAxis: STORM_KP }],
          },
        },
      ],
    };
  }, [theme, readings, locale, t]);

  return (
    <DataRegion query={query} minHeight={420}>
      {(data) => (
        <ChartFigure<KpReading>
          title={t('sun.kp.title')}
          description={t('sun.kp.description')}
          option={option}
          height={300}
          sources={['swpc']}
          rows={[...data.items].reverse()}
          rowKey={(reading) => reading.observed_at}
          columns={[
            {
              key: 'time',
              header: t('common.date'),
              cell: (reading) => formatDateTime(locale, reading.observed_at),
            },
            {
              key: 'kp',
              header: t('units.kp'),
              numeric: true,
              cell: (reading) => decimal(locale, reading.kp, 2),
            },
            {
              key: 'g',
              header: t('common.status'),
              cell: (reading) => (
                <span lang={reading.g_scale.name_lang}>{reading.g_scale.name}</span>
              ),
            },
          ]}
        />
      )}
    </DataRegion>
  );
}

function flareClassOf(flux: number): string {
  const index = Math.min(FLARE_CLASSES.length - 1, Math.max(0, Math.floor(Math.log10(flux)) + 8));
  return FLARE_CLASSES[index] ?? 'A';
}

function FlareChart() {
  const { t } = useTranslation();
  const locale = useLocale();
  const theme = useChartTheme();
  const query = useQuery(
    flaresQuery(locale, { from: hoursAgo(WEEK_HOURS), size: 100, sort: '-time' }),
  );
  const flares = useMemo(
    () => (query.data?.items ?? []).filter((flare) => flare.peak_flux_wm2 !== undefined),
    [query.data],
  );
  const option = useMemo<ChartOption>(() => {
    const axis = axisStyle(theme);
    return {
      ...baseOption(theme),
      tooltip: {
        ...baseOption(theme).tooltip,
        trigger: 'item',
        formatter: (item: { data: { flare: Flare } }) =>
          `<strong>${item.data.flare.xray_class ?? ''}</strong><br/>${formatDateTime(locale, item.data.flare.peak_at ?? item.data.flare.begin_at ?? item.data.flare.id)}`,
      },
      xAxis: timeAxis(theme, locale),
      yAxis: {
        type: 'log',
        min: 1e-8,
        max: 1e-3,
        ...axis,
        axisLabel: {
          ...axis.axisLabel,
          formatter: (value: number) => (value >= 1e-3 ? '' : flareClassOf(value)),
        },
      },
      series: [
        {
          type: 'scatter',
          name: t('sun.flares.title'),
          symbolSize: 9,
          data: flares.map((flare) => ({
            value: [flare.peak_at ?? flare.begin_at, flare.peak_flux_wm2],
            flare,
            itemStyle: {
              color: (flare.peak_flux_wm2 ?? 0) >= 1e-5 ? theme.warm : theme.cool,
              borderColor: theme.canvas,
              borderWidth: 1,
            },
          })),
        },
      ],
    };
  }, [theme, flares, locale, t]);

  return (
    <DataRegion query={query} minHeight={420}>
      {() => (
        <ChartFigure<Flare>
          title={t('sun.flares.title')}
          description={t('sun.flares.description')}
          option={option}
          height={300}
          sources={['swpc']}
          rows={flares}
          rowKey={(flare) => flare.id}
          columns={[
            {
              key: 'peak',
              header: t('common.date'),
              cell: (flare) => formatDateTime(locale, flare.peak_at ?? flare.begin_at ?? flare.id),
            },
            { key: 'class', header: 'X-ray', cell: (flare) => flare.xray_class ?? '—' },
            {
              key: 'r',
              header: t('common.status'),
              cell: (flare) =>
                flare.r_scale === undefined ? (
                  '—'
                ) : (
                  <span lang={flare.r_scale.name_lang}>{flare.r_scale.name}</span>
                ),
            },
          ]}
        />
      )}
    </DataRegion>
  );
}

function windOption(
  theme: ChartTheme,
  locale: Locale,
  points: readonly WindPoint[],
  pick: (point: WindPoint) => number | undefined,
  color: string,
  name: string,
  zeroLine: boolean,
): ChartOption {
  const axis = axisStyle(theme);
  return {
    ...baseOption(theme),
    tooltip: {
      ...baseOption(theme).tooltip,
      trigger: 'axis',
      valueFormatter: (value: number) => decimal(locale, value),
    },
    xAxis: timeAxis(theme, locale),
    yAxis: { type: 'value', scale: true, ...axis },
    series: [
      {
        type: 'line',
        name,
        showSymbol: false,
        lineStyle: { width: 1.5, color },
        itemStyle: { color },
        data: points.map((point) => [point.observed_at, pick(point) ?? null]),
        ...(zeroLine
          ? {
              markLine: {
                silent: true,
                symbol: 'none',
                lineStyle: { color: theme.muted, type: 'dashed' },
                label: { show: false },
                data: [{ yAxis: 0 }],
              },
            }
          : {}),
      },
    ],
  };
}

function SolarWind() {
  const { t } = useTranslation();
  const locale = useLocale();
  const theme = useChartTheme();
  const query = useQuery(
    solarWindQuery(locale, { resolution: 'hour', from: hoursAgo(WEEK_HOURS) }),
  );
  const points = useMemo(() => query.data?.items ?? [], [query.data]);
  const speed = useMemo(
    () =>
      windOption(
        theme,
        locale,
        points,
        (point) => point.speed_kms,
        theme.cool,
        t('sun.wind.speed'),
        false,
      ),
    [theme, locale, points, t],
  );
  const bz = useMemo(
    () =>
      windOption(
        theme,
        locale,
        points,
        (point) => point.bz_gsm_nt,
        theme.warm,
        t('sun.wind.bz'),
        true,
      ),
    [theme, locale, points, t],
  );
  const columns = [
    {
      key: 'time',
      header: t('common.date'),
      cell: (point: WindPoint) => formatDateTime(locale, point.observed_at),
    },
    {
      key: 'speed',
      header: t('sun.wind.speed'),
      numeric: true,
      cell: (point: WindPoint) =>
        point.speed_kms === undefined ? '—' : decimal(locale, point.speed_kms, 0),
    },
    {
      key: 'bz',
      header: t('sun.wind.bz'),
      numeric: true,
      cell: (point: WindPoint) =>
        point.bz_gsm_nt === undefined ? '—' : decimal(locale, point.bz_gsm_nt),
    },
  ];

  return (
    <DataRegion query={query} minHeight={380}>
      {() => (
        <div className="grid gap-12 lg:grid-cols-2">
          <ChartFigure
            title={t('sun.wind.speed')}
            description={t('sun.wind.speedDescription')}
            option={speed}
            height={240}
            sources={['swpc']}
            rows={[...points].reverse()}
            rowKey={(point) => point.observed_at}
            columns={columns}
            visibleTitle
          />
          <ChartFigure
            title={t('sun.wind.bz')}
            description={t('sun.wind.bzDescription')}
            option={bz}
            height={240}
            sources={['swpc']}
            rows={[...points].reverse()}
            rowKey={(point) => point.observed_at}
            columns={columns}
            visibleTitle
          />
        </div>
      )}
    </DataRegion>
  );
}

function AuroraHistory({ aurora }: { aurora: Aurora }) {
  const { t } = useTranslation();
  const locale = useLocale();
  const theme = useChartTheme();
  const option = useMemo<ChartOption>(() => {
    const axis = axisStyle(theme);
    const line = (
      name: string,
      color: string,
      pick: (summary: Aurora['history'][number]) => number,
    ) => ({
      type: 'line' as const,
      name,
      showSymbol: aurora.history.length < 24,
      symbolSize: 5,
      lineStyle: { width: 2, color },
      itemStyle: { color },
      data: aurora.history.map((summary) => [summary.observed_at, pick(summary)]),
    });
    return {
      ...baseOption(theme),
      tooltip: {
        ...baseOption(theme).tooltip,
        trigger: 'axis',
        valueFormatter: (value: number) => `${String(value)}%`,
      },
      xAxis: {
        ...timeAxis(theme, locale),
        axisLabel: {
          ...axis.axisLabel,
          hideOverlap: true,
          formatter: (value: number) =>
            new Intl.DateTimeFormat(locale === 'ja' ? 'ja-JP' : 'en-US', {
              hour: 'numeric',
              day: 'numeric',
            }).format(new Date(value)),
        },
      },
      yAxis: {
        type: 'value',
        min: 0,
        ...axis,
        axisLabel: { ...axis.axisLabel, formatter: '{value}%' },
      },
      series: [
        line(t('sun.aurora.north'), theme.cool, (summary) => summary.north_max_percent),
        line(t('sun.aurora.south'), theme.warm, (summary) => summary.south_max_percent),
      ],
    };
  }, [theme, aurora, locale, t]);

  return (
    <ChartFigure
      legend={[
        { label: t('sun.aurora.north'), color: theme.cool },
        { label: t('sun.aurora.south'), color: theme.warm },
      ]}
      title={t('sun.aurora.history')}
      description={t('sun.aurora.historyDescription')}
      option={option}
      height={220}
      sources={['swpc']}
      rows={[...aurora.history].reverse()}
      rowKey={(summary) => summary.observed_at}
      columns={[
        {
          key: 'time',
          header: t('common.date'),
          cell: (summary) => formatDateTime(locale, summary.observed_at),
        },
        {
          key: 'north',
          header: t('sun.aurora.north'),
          numeric: true,
          cell: (summary) => `${String(summary.north_max_percent)}%`,
        },
        {
          key: 'south',
          header: t('sun.aurora.south'),
          numeric: true,
          cell: (summary) => `${String(summary.south_max_percent)}%`,
        },
      ]}
      visibleTitle
    />
  );
}

function AuroraPanel() {
  const { t } = useTranslation();
  const locale = useLocale();
  const query = useQuery(auroraQuery(locale, { min_percent: 1 }));
  const [hemisphere, setHemisphere] = useState<Hemisphere>('north');

  return (
    <DataRegion query={query} minHeight={560}>
      {(aurora) => {
        const latest = aurora.latest;
        if (latest === undefined) {
          return <p className="text-ink-muted">{t('common.none')}</p>;
        }
        const side = latest[hemisphere];
        const percent = (value: number) =>
          value < 1 ? t('common.lessThanOne') : `${String(value)}%`;
        const places = PLACES.filter((place) =>
          hemisphere === 'north' ? place.latitude > 0 : place.latitude < 0,
        );
        return (
          <div className="flex flex-col gap-14">
            <div className="grid items-start gap-12 lg:grid-cols-[minmax(0,560px)_minmax(0,1fr)]">
              <div className="flex flex-col gap-4">
                <div
                  role="group"
                  aria-label={t('sun.aurora.title')}
                  className="flex w-fit rounded-pill border border-hairline p-0.5"
                >
                  {(['north', 'south'] as const).map((option) => (
                    <button
                      key={option}
                      type="button"
                      aria-pressed={hemisphere === option}
                      onClick={() => {
                        setHemisphere(option);
                      }}
                      className={`rounded-pill px-3 py-1 text-xs transition-colors duration-[var(--hz-duration-fast)] ${hemisphere === option ? 'bg-surface-raised text-ink' : 'text-ink-muted hover:text-ink'}`}
                    >
                      {t(`sun.aurora.${option}`)}
                    </button>
                  ))}
                </div>
                <AuroraMap cells={latest.cells} hemisphere={hemisphere} />
                <p className="text-sm text-ink-muted">
                  {t('sun.aurora.forecastFor', {
                    time: formatDateTime(locale, latest.forecast_at),
                  })}
                </p>
              </div>
              <div className="flex flex-col gap-8">
                <div className="grid gap-8 sm:grid-cols-2">
                  <StatTile label={t('sun.aurora.peak')} value={`${String(side.max_percent)}%`} />
                  <StatTile
                    label={t('sun.aurora.boundary')}
                    value={
                      side.boundary_lat === undefined
                        ? '—'
                        : `${String(Math.abs(side.boundary_lat))}°${hemisphere === 'north' ? 'N' : 'S'}`
                    }
                    {...(side.boundary_lat === undefined
                      ? { detail: t('sun.aurora.boundaryNone') }
                      : {})}
                  />
                </div>
                <div className="flex flex-col gap-3">
                  <h3 className="font-display text-xl font-light text-ink">
                    {t('sun.aurora.places')}
                  </h3>
                  <DataTable
                    caption={t('sun.aurora.places')}
                    rows={places}
                    rowKey={(place) => place.key}
                    columns={[
                      {
                        key: 'place',
                        header: t('sun.aurora.place'),
                        cell: (place) => t(`places.${place.key}`),
                      },
                      {
                        key: 'chance',
                        header: t('sun.aurora.chance'),
                        numeric: true,
                        cell: (place) =>
                          percent(chanceAt(latest.cells, place.longitude, place.latitude)),
                      },
                    ]}
                  />
                </div>
                <SourceNote sources={['swpc']} asOf={latest.observed_at} />
              </div>
            </div>
            <AuroraHistory aurora={aurora} />
          </div>
        );
      }}
    </DataRegion>
  );
}

export function SunPage() {
  const { t } = useTranslation();
  useDocumentTitle(t('pages.sun.title'));

  return (
    <PageLayout title={t('pages.sun.title')} lede={t('pages.sun.lede')}>
      <Section id="sun-now" title={t('sun.now')}>
        <Now />
      </Section>
      <Section id="sun-facts" title={t('sun.facts')}>
        <ModuleFacts module="space-weather" />
      </Section>
      <Section id="sun-aurora" title={t('sun.aurora.title')} lede={t('sun.aurora.lede')}>
        <AuroraPanel />
      </Section>
      <Section id="sun-kp" title={t('sun.kp.title')} lede={t('sun.kp.lede')}>
        <KpChart />
      </Section>
      <Section id="sun-flares" title={t('sun.flares.title')} lede={t('sun.flares.lede')}>
        <FlareChart />
      </Section>
      <Section id="sun-wind" title={t('sun.wind.title')} lede={t('sun.wind.lede')}>
        <SolarWind />
      </Section>
    </PageLayout>
  );
}
