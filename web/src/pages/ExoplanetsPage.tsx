import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  exoplanetDiscoveriesQuery,
  exoplanetSizeOrbitQuery,
  exoplanetsQuery,
  type Schemas,
} from '../api/queries';
import { useDocumentTitle } from '../app/useDocumentTitle';
import type { ChartOption } from '../charts/echarts';
import { axisStyle, baseOption, seriesColor } from '../charts/theme';
import { useChartTheme } from '../charts/useChartTheme';
import { ChartFigure } from '../components/ChartFigure';
import { DataRegion } from '../components/DataRegion';
import { DataTable } from '../components/DataTable';
import { ModuleFacts } from '../components/ModuleFacts';
import { PageLayout } from '../components/PageLayout';
import { Section } from '../components/Section';
import { SourceNote } from '../components/SourceNote';
import { formatNumber } from '../format/format';
import type { Locale } from '../i18n/locales';
import { useLocale } from '../i18n/useLocale';

const SOURCE = 'exoplanet-archive';
const FIRST_YEAR = 1995;
const SHOWN_METHODS = 4;
const EARTH = { periodDays: 365.25, radiusEarth: 1 };
const JUPITER = { periodDays: 4332.6, radiusEarth: 11.21 };

type DiscoveryYear = Schemas['ExoplanetDiscoveryYear'];
type Cell = Schemas['ExoplanetSizeOrbitCell'];
type Planet = Schemas['Exoplanet'];

interface DiscoveryRow {
  readonly year: number;
  readonly counts: readonly number[];
  readonly total: number;
}

function discoveryRows(years: readonly DiscoveryYear[], codes: readonly string[]): DiscoveryRow[] {
  return years.map((year) => {
    const byCode = new Map(year.methods.map((method) => [method.code, method.planets]));
    const shown = codes.map((code) => byCode.get(code) ?? 0);
    const other = year.planets - shown.reduce((sum, count) => sum + count, 0);
    return { year: year.year, counts: [...shown, other], total: year.planets };
  });
}

function Discoveries() {
  const { t } = useTranslation();
  const locale = useLocale();
  const theme = useChartTheme();
  const lastYear = new Date().getUTCFullYear() - 1;
  const query = useQuery(
    exoplanetDiscoveriesQuery(locale, { from_year: FIRST_YEAR, to_year: lastYear }),
  );
  const methods = useMemo(() => (query.data?.methods ?? []).slice(0, SHOWN_METHODS), [query.data]);
  const names = useMemo(
    () => [...methods.map((method) => method.method.name), t('common.other')],
    [methods, t],
  );
  const rows = useMemo(
    () =>
      discoveryRows(
        query.data?.years ?? [],
        methods.map((method) => method.method.code),
      ),
    [query.data, methods],
  );
  const colors = useMemo(
    () => [...methods.map((_, index) => seriesColor(theme, index)), theme.other],
    [methods, theme],
  );
  const option = useMemo<ChartOption>(() => {
    const axis = axisStyle(theme);
    return {
      ...baseOption(theme),
      grid: { left: 8, right: 8, top: 24, bottom: 8, containLabel: true },
      tooltip: { ...baseOption(theme).tooltip, trigger: 'axis', axisPointer: { type: 'shadow' } },
      xAxis: {
        type: 'category',
        data: rows.map((row) => String(row.year)),
        ...axis,
        splitLine: { show: false },
      },
      yAxis: { type: 'value', ...axis },
      series: names.map((name, index) => ({
        type: 'bar' as const,
        name,
        stack: 'planets',
        data: rows.map((row) => row.counts[index] ?? 0),
        barMaxWidth: 16,
        itemStyle: { color: colors[index] },
      })),
    };
  }, [theme, rows, names, colors]);

  return (
    <DataRegion query={query} minHeight={500}>
      {() => (
        <ChartFigure
          legend={names.map((label, index) => ({ label, color: colors[index] ?? theme.other }))}
          title={t('exoplanets.discoveries.title')}
          description={t('exoplanets.discoveries.description')}
          option={option}
          height={380}
          sources={[SOURCE]}
          rows={[...rows].reverse()}
          rowKey={(row) => String(row.year)}
          columns={[
            { key: 'year', header: t('common.year'), cell: (row) => row.year },
            ...names.map((name, index) => ({
              key: `method-${String(index)}`,
              header: name,
              numeric: true,
              cell: (row: DiscoveryRow) => formatNumber(locale, row.counts[index] ?? 0),
            })),
            {
              key: 'total',
              header: t('exoplanets.planets'),
              numeric: true,
              cell: (row) => formatNumber(locale, row.total),
            },
          ]}
        />
      )}
    </DataRegion>
  );
}

function geometricMiddle(min: number, max: number): number {
  return Math.sqrt(min * max);
}

function range(locale: Locale, min: number, max: number, digits: number): string {
  const format = (value: number) =>
    formatNumber(locale, value, { maximumSignificantDigits: digits });
  return `${format(min)}–${format(max)}`;
}

function SizeOrbit() {
  const { t } = useTranslation();
  const locale = useLocale();
  const theme = useChartTheme();
  const query = useQuery(exoplanetSizeOrbitQuery(locale));
  const cells = useMemo<Cell[]>(() => query.data?.cells ?? [], [query.data]);
  const option = useMemo<ChartOption>(() => {
    const axis = axisStyle(theme);
    const largest = Math.max(1, ...cells.map((cell) => cell.planets));
    const reference = (name: string, point: { periodDays: number; radiusEarth: number }) => ({
      name,
      value: [point.periodDays, point.radiusEarth],
      label: { show: true, formatter: name, position: 'right' as const, color: theme.ink },
    });
    return {
      ...baseOption(theme),
      grid: { left: 8, right: 24, top: 24, bottom: 36, containLabel: true },
      tooltip: {
        ...baseOption(theme).tooltip,
        trigger: 'item',
        formatter: (item: { data: { cell?: Cell; name?: string } }) => {
          const cell = item.data.cell;
          if (cell === undefined) {
            return item.data.name ?? '';
          }
          return [
            `${t('exoplanets.sizeOrbit.period')}: ${range(locale, cell.period_min_days, cell.period_max_days, 3)}`,
            `${t('exoplanets.sizeOrbit.radius')}: ${range(locale, cell.radius_min_earth, cell.radius_max_earth, 2)}`,
            `${t('exoplanets.planets')}: ${formatNumber(locale, cell.planets)}`,
          ].join('<br/>');
        },
      },
      xAxis: {
        type: 'log',
        name: t('exoplanets.sizeOrbit.period'),
        nameLocation: 'middle',
        nameGap: 28,
        ...axis,
      },
      yAxis: {
        type: 'log',
        name: t('exoplanets.sizeOrbit.radius'),
        ...axis,
        nameTextStyle: { ...axis.nameTextStyle, align: 'left' },
      },
      series: [
        {
          type: 'scatter',
          name: t('exoplanets.planets'),
          data: cells.map((cell) => ({
            value: [
              geometricMiddle(cell.period_min_days, cell.period_max_days),
              geometricMiddle(cell.radius_min_earth, cell.radius_max_earth),
            ],
            cell,
          })),
          symbolSize: (_: unknown, params: { data: { cell: Cell } }) =>
            4 + 22 * Math.sqrt(params.data.cell.planets / largest),
          itemStyle: { color: theme.cool, opacity: 0.75 },
        },
        {
          type: 'scatter',
          name: t('exoplanets.sizeOrbit.reference'),
          data: [
            reference(t('exoplanets.sizeOrbit.earth'), EARTH),
            reference(t('exoplanets.sizeOrbit.jupiter'), JUPITER),
          ],
          symbol: 'diamond',
          symbolSize: 12,
          itemStyle: { color: theme.warm, borderColor: theme.canvas, borderWidth: 2 },
        },
      ],
    };
  }, [theme, cells, locale, t]);

  return (
    <DataRegion query={query} minHeight={520}>
      {() => (
        <ChartFigure
          legend={[
            { label: t('exoplanets.planets'), color: theme.cool },
            { label: t('exoplanets.sizeOrbit.reference'), color: theme.warm },
          ]}
          title={t('exoplanets.sizeOrbit.title')}
          description={t('exoplanets.sizeOrbit.description')}
          option={option}
          height={420}
          sources={[SOURCE]}
          rows={[...cells].sort((a, b) => b.planets - a.planets)}
          rowKey={(cell) => `${String(cell.period_min_days)}|${String(cell.radius_min_earth)}`}
          columns={[
            {
              key: 'period',
              header: t('exoplanets.sizeOrbit.period'),
              cell: (cell) => range(locale, cell.period_min_days, cell.period_max_days, 3),
            },
            {
              key: 'radius',
              header: t('exoplanets.sizeOrbit.radius'),
              cell: (cell) => range(locale, cell.radius_min_earth, cell.radius_max_earth, 2),
            },
            {
              key: 'planets',
              header: t('exoplanets.planets'),
              numeric: true,
              cell: (cell) => formatNumber(locale, cell.planets),
            },
          ]}
        />
      )}
    </DataRegion>
  );
}

function optional(locale: Locale, value: number | undefined, digits: number): string {
  return value === undefined ? '—' : formatNumber(locale, value, { maximumFractionDigits: digits });
}

function Nearest() {
  const { t } = useTranslation();
  const locale = useLocale();
  const query = useQuery(exoplanetsQuery(locale, { sort: 'distance', size: 10 }));

  return (
    <DataRegion query={query} minHeight={420}>
      {(page) => (
        <div className="flex flex-col gap-4">
          <DataTable<Planet>
            caption={t('exoplanets.nearest.title')}
            rows={page.items}
            rowKey={(planet) => planet.name}
            columns={[
              { key: 'name', header: t('exoplanets.planet'), cell: (planet) => planet.name },
              {
                key: 'distance',
                header: t('exoplanets.distanceLy'),
                numeric: true,
                cell: (planet) =>
                  planet.distance_ly === undefined
                    ? '—'
                    : formatNumber(locale, planet.distance_ly, {
                        minimumFractionDigits: 1,
                        maximumFractionDigits: 1,
                      }),
              },
              {
                key: 'radius',
                header: t('exoplanets.radius'),
                numeric: true,
                cell: (planet) => optional(locale, planet.radius_earth, 2),
              },
              {
                key: 'period',
                header: t('exoplanets.period'),
                numeric: true,
                cell: (planet) => optional(locale, planet.orbital_period_days, 1),
              },
              {
                key: 'method',
                header: t('exoplanets.method'),
                cell: (planet) => (
                  <span lang={planet.discovery.method.name_lang}>
                    {planet.discovery.method.name}
                  </span>
                ),
              },
              {
                key: 'year',
                header: t('exoplanets.discovered'),
                numeric: true,
                cell: (planet) => planet.discovery.year ?? '—',
              },
            ]}
          />
          <p className="max-w-3xl text-sm text-ink-muted">{t('exoplanets.nearest.note')}</p>
          <SourceNote sources={[SOURCE]} />
        </div>
      )}
    </DataRegion>
  );
}

export function ExoplanetsPage() {
  const { t } = useTranslation();
  useDocumentTitle(t('pages.exoplanets.title'));

  return (
    <PageLayout title={t('pages.exoplanets.title')} lede={t('pages.exoplanets.lede')}>
      <Section id="exoplanet-facts" title={t('exoplanets.facts')}>
        <ModuleFacts module="exoplanets" />
      </Section>
      <Section
        id="exoplanet-discoveries"
        title={t('exoplanets.discoveries.title')}
        lede={t('exoplanets.discoveries.lede')}
      >
        <Discoveries />
      </Section>
      <Section
        id="exoplanet-size-orbit"
        title={t('exoplanets.sizeOrbit.title')}
        lede={t('exoplanets.sizeOrbit.lede')}
      >
        <SizeOrbit />
      </Section>
      <Section
        id="exoplanet-nearest"
        title={t('exoplanets.nearest.title')}
        lede={t('exoplanets.nearest.lede')}
      >
        <Nearest />
      </Section>
      <p className="max-w-3xl text-sm text-ink-muted">{t('exoplanets.acknowledgment')}</p>
    </PageLayout>
  );
}
