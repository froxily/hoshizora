import { useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  hoursAgo,
  launchBoostersQuery,
  launchCadenceQuery,
  launchesQuery,
  launchPadsQuery,
  launchReusabilityQuery,
  launchSuccessQuery,
  type Schemas,
} from '../api/queries';
import { useDocumentTitle } from '../app/useDocumentTitle';
import type { ChartOption } from '../charts/echarts';
import { axisStyle, baseOption, seriesColor, type ChartTheme } from '../charts/theme';
import { useChartTheme } from '../charts/useChartTheme';
import { ChartFigure } from '../components/ChartFigure';
import { DataRegion } from '../components/DataRegion';
import { LaunchTable } from '../components/LaunchTable';
import { ModuleFacts } from '../components/ModuleFacts';
import { PageLayout } from '../components/PageLayout';
import { Section } from '../components/Section';
import { formatDate, formatNumber } from '../format/format';
import type { Locale } from '../i18n/locales';
import { useLocale } from '../i18n/useLocale';

const FIRST_YEAR = 1957;
const PROGRAMS = 6;

type Series = Schemas['LaunchCadenceSeries'];
type ReuseYear = Schemas['LaunchReusabilityYear'];

const REUSE_FROM_YEAR = 2015;

interface CadenceRow {
  readonly year: number;
  readonly values: readonly number[];
  readonly world: number;
}

function percent(locale: Locale, value: number): string {
  return formatNumber(locale, value, { style: 'percent', maximumFractionDigits: 1 });
}

function attemptsByYear(series: Series | undefined): Map<number, number> {
  return new Map((series?.years ?? []).map((year) => [year.year, year.attempts]));
}

function cadenceRows(programs: readonly Series[], world: Series | undefined): CadenceRow[] {
  const worldYears = attemptsByYear(world);
  const byProgram = programs.map(attemptsByYear);
  const lastYear = new Date().getUTCFullYear() - 1;
  return Array.from({ length: lastYear - FIRST_YEAR + 1 }, (_, index) => FIRST_YEAR + index).map(
    (year) => ({
      year,
      values: byProgram.map((years) => years.get(year) ?? 0),
      world: worldYears.get(year) ?? 0,
    }),
  );
}

const END_LABEL_WIDTH = 108;

function cadenceOption(
  theme: ChartTheme,
  programs: readonly Series[],
  rows: readonly CadenceRow[],
  worldName: string,
): ChartOption {
  const axis = axisStyle(theme);
  const finalValues = programs.map((_, index) => rows.at(-1)?.values[index] ?? 0);
  const labelled = new Set(
    [...finalValues.keys()]
      .sort((a, b) => (finalValues[b] ?? 0) - (finalValues[a] ?? 0))
      .slice(0, 3),
  );
  const line = (name: string, color: string, data: number[], width: number, label: boolean) => ({
    type: 'line' as const,
    name,
    data,
    showSymbol: false,
    lineStyle: { width, color },
    itemStyle: { color },
    emphasis: { focus: 'series' as const },
    endLabel: {
      show: label,
      formatter: '{a}',
      color: theme.ink,
      fontSize: 11,
      width: END_LABEL_WIDTH,
      overflow: 'break' as const,
      lineHeight: 14,
    },
  });
  return {
    ...baseOption(theme),
    grid: { left: 8, right: END_LABEL_WIDTH + 12, top: 48, bottom: 8, containLabel: true },
    tooltip: { ...baseOption(theme).tooltip, trigger: 'axis', order: 'valueDesc' },
    xAxis: {
      type: 'category',
      data: rows.map((row) => String(row.year)),
      ...axis,
      splitLine: { show: false },
    },
    yAxis: { type: 'value', ...axis },
    series: [
      line(
        worldName,
        theme.other,
        rows.map((row) => row.world),
        1.5,
        true,
      ),
      ...programs.map((program, index) =>
        line(
          program.group.name,
          seriesColor(theme, index),
          rows.map((row) => row.values[index] ?? 0),
          2,
          labelled.has(index),
        ),
      ),
    ],
  };
}

function Cadence() {
  const { t } = useTranslation();
  const locale = useLocale();
  const theme = useChartTheme();
  const programs = useQuery(
    launchCadenceQuery(locale, { group_by: 'program', limit: PROGRAMS, from_year: FIRST_YEAR }),
  );
  const world = useQuery(launchCadenceQuery(locale, { group_by: 'all', from_year: FIRST_YEAR }));
  const ready = programs.data !== undefined && world.data !== undefined;
  const groups = useMemo(() => programs.data?.groups ?? [], [programs.data]);
  const rows = useMemo(
    () => (ready ? cadenceRows(groups, world.data.groups[0]) : []),
    [ready, groups, world.data],
  );
  const option = useMemo(
    () => cadenceOption(theme, groups, rows, t('common.world')),
    [theme, groups, rows, t],
  );

  return (
    <DataRegion query={ready ? world : programs} minHeight={540}>
      {() => (
        <ChartFigure
          legend={[
            { label: t('common.world'), color: theme.other },
            ...groups.map((group, index) => ({
              label: group.group.name,
              color: seriesColor(theme, index),
            })),
          ]}
          title={t('launches.cadence.title')}
          description={t('launches.cadence.description')}
          option={option}
          height={420}
          sources={['launch-library']}
          rows={[...rows].reverse()}
          rowKey={(row) => String(row.year)}
          columns={[
            { key: 'year', header: t('common.year'), cell: (row) => row.year },
            ...groups.map((group, index) => ({
              key: group.group.key,
              header: group.group.name,
              numeric: true,
              cell: (row: CadenceRow) => formatNumber(locale, row.values[index] ?? 0),
            })),
            {
              key: 'world',
              header: t('common.world'),
              numeric: true,
              cell: (row) => formatNumber(locale, row.world),
            },
          ]}
        />
      )}
    </DataRegion>
  );
}

function Success() {
  const { t } = useTranslation();
  const locale = useLocale();
  const theme = useChartTheme();
  const query = useQuery(launchSuccessQuery(locale, { group_by: 'program', limit: 8 }));
  const groups = useMemo(() => [...(query.data?.groups ?? [])].reverse(), [query.data]);
  const option = useMemo<ChartOption>(() => {
    const axis = axisStyle(theme);
    return {
      ...baseOption(theme),
      grid: { left: 8, right: 24, top: 40, bottom: 8, containLabel: true },
      tooltip: { ...baseOption(theme).tooltip, trigger: 'axis', axisPointer: { type: 'shadow' } },
      xAxis: {
        type: 'value',
        min: 0,
        max: 1,
        ...axis,
        axisLabel: { ...axis.axisLabel, formatter: (value: number) => percent(locale, value) },
      },
      yAxis: {
        type: 'category',
        data: groups.map((group) => group.group.name),
        ...axis,
        splitLine: { show: false },
      },
      series: [
        {
          type: 'bar',
          name: t('common.successRate'),
          data: groups.map((group) => group.success_rate ?? null),
          barWidth: 10,
          itemStyle: { color: theme.cool, borderRadius: [0, 4, 4, 0] },
          tooltip: { valueFormatter: (value: number) => percent(locale, value) },
        },
        {
          type: 'scatter',
          name: t('common.recentRate'),
          data: groups.map((group) => group.recent_success_rate ?? null),
          symbol: 'diamond',
          symbolSize: 11,
          itemStyle: { color: theme.warm, borderColor: theme.canvas, borderWidth: 2 },
          tooltip: { valueFormatter: (value: number) => percent(locale, value) },
        },
      ],
    };
  }, [theme, groups, locale, t]);

  return (
    <DataRegion query={query} minHeight={480}>
      {(data) => (
        <ChartFigure
          legend={[
            { label: t('common.successRate'), color: theme.cool },
            { label: t('common.recentRate'), color: theme.warm },
          ]}
          title={t('launches.success.title')}
          description={t('launches.success.description')}
          option={option}
          height={360}
          sources={['launch-library']}
          rows={data.groups}
          rowKey={(group) => group.group.key}
          columns={[
            { key: 'name', header: t('common.name'), cell: (group) => group.group.name },
            {
              key: 'attempts',
              header: t('common.attempts'),
              numeric: true,
              cell: (group) => formatNumber(locale, group.attempts),
            },
            {
              key: 'rate',
              header: t('common.successRate'),
              numeric: true,
              cell: (group) =>
                group.success_rate === undefined ? '—' : percent(locale, group.success_rate),
            },
            {
              key: 'recent',
              header: t('common.recentRate'),
              numeric: true,
              cell: (group) =>
                group.recent_success_rate === undefined
                  ? '—'
                  : percent(locale, group.recent_success_rate),
            },
          ]}
        />
      )}
    </DataRegion>
  );
}

function rate(locale: Locale, value: number | undefined): string {
  return value === undefined ? '—' : percent(locale, value);
}

function Reusability() {
  const { t } = useTranslation();
  const locale = useLocale();
  const theme = useChartTheme();
  const lastYear = new Date().getUTCFullYear() - 1;
  const query = useQuery(
    launchReusabilityQuery(locale, {
      group_by: 'all',
      from_year: REUSE_FROM_YEAR,
      to_year: lastYear,
    }),
  );
  const years = useMemo<ReuseYear[]>(() => query.data?.groups[0]?.years ?? [], [query.data]);
  const option = useMemo<ChartOption>(() => {
    const axis = axisStyle(theme);
    const bar = (name: string, color: string, data: number[]) => ({
      type: 'bar' as const,
      name,
      stack: 'launches',
      data,
      barMaxWidth: 18,
      itemStyle: { color },
    });
    return {
      ...baseOption(theme),
      grid: { left: 8, right: 8, top: 40, bottom: 8, containLabel: true },
      tooltip: { ...baseOption(theme).tooltip, trigger: 'axis', axisPointer: { type: 'shadow' } },
      xAxis: {
        type: 'category',
        data: years.map((year) => String(year.year)),
        ...axis,
        splitLine: { show: false },
      },
      yAxis: [
        { type: 'value', ...axis },
        {
          type: 'value',
          min: 0,
          max: 1,
          ...axis,
          splitLine: { show: false },
          axisLabel: { ...axis.axisLabel, formatter: (value: number) => percent(locale, value) },
        },
      ],
      series: [
        bar(
          t('launches.reusability.reflown'),
          theme.warm,
          years.map((year) => year.launches_reflown),
        ),
        bar(
          t('launches.reusability.fresh'),
          theme.other,
          years.map((year) => year.launches - year.launches_reflown),
        ),
        {
          type: 'line',
          name: t('launches.reusability.landingRate'),
          yAxisIndex: 1,
          data: years.map((year) => year.landing_success_rate ?? null),
          showSymbol: true,
          symbolSize: 6,
          lineStyle: { width: 2, color: theme.cool },
          itemStyle: { color: theme.cool },
          tooltip: { valueFormatter: (value: number) => percent(locale, value) },
        },
      ],
    };
  }, [theme, years, locale, t]);

  return (
    <DataRegion query={query} minHeight={500}>
      {() => (
        <ChartFigure
          legend={[
            { label: t('launches.reusability.reflown'), color: theme.warm },
            { label: t('launches.reusability.fresh'), color: theme.other },
            { label: t('launches.reusability.landingRate'), color: theme.cool },
          ]}
          title={t('launches.reusability.title')}
          description={t('launches.reusability.description')}
          option={option}
          height={380}
          sources={['launch-library']}
          rows={[...years].reverse()}
          rowKey={(year) => String(year.year)}
          columns={[
            { key: 'year', header: t('common.year'), cell: (year) => year.year },
            {
              key: 'launches',
              header: t('launches.reusability.launches'),
              numeric: true,
              cell: (year) => formatNumber(locale, year.launches),
            },
            {
              key: 'reflown',
              header: t('launches.reusability.reflown'),
              numeric: true,
              cell: (year) => formatNumber(locale, year.launches_reflown),
            },
            {
              key: 'landings',
              header: t('launches.reusability.landings'),
              numeric: true,
              cell: (year) => formatNumber(locale, year.landings),
            },
            {
              key: 'rate',
              header: t('launches.reusability.landingRate'),
              numeric: true,
              cell: (year) => rate(locale, year.landing_success_rate),
            },
          ]}
        />
      )}
    </DataRegion>
  );
}

function Boosters() {
  const { t } = useTranslation();
  const locale = useLocale();
  const theme = useChartTheme();
  const query = useQuery(launchBoostersQuery(locale, { limit: 10 }));
  const boosters = useMemo(() => [...(query.data?.items ?? [])].reverse(), [query.data]);
  const option = useMemo<ChartOption>(() => {
    const axis = axisStyle(theme);
    return {
      ...baseOption(theme),
      grid: { left: 8, right: 40, top: 8, bottom: 8, containLabel: true },
      tooltip: { ...baseOption(theme).tooltip, trigger: 'axis', axisPointer: { type: 'shadow' } },
      xAxis: { type: 'value', ...axis },
      yAxis: {
        type: 'category',
        data: boosters.map((booster) => booster.serial_number),
        ...axis,
        splitLine: { show: false },
      },
      series: [
        {
          type: 'bar',
          name: t('launches.boosters.flights'),
          data: boosters.map((booster) => booster.flights),
          barWidth: 10,
          itemStyle: { color: theme.warm, borderRadius: [0, 4, 4, 0] },
          label: { show: true, position: 'right', color: theme.ink, fontSize: 11 },
        },
      ],
    };
  }, [theme, boosters, t]);

  return (
    <DataRegion query={query} minHeight={500}>
      {(data) => (
        <ChartFigure
          title={t('launches.boosters.title')}
          description={t('launches.boosters.description')}
          option={option}
          height={380}
          sources={['launch-library']}
          rows={data.items}
          rowKey={(booster) => String(booster.id)}
          columns={[
            {
              key: 'serial',
              header: t('launches.boosters.serial'),
              cell: (booster) => booster.serial_number,
            },
            {
              key: 'vehicle',
              header: t('launches.boosters.vehicle'),
              cell: (booster) => booster.vehicle?.name ?? '—',
            },
            {
              key: 'flights',
              header: t('launches.boosters.flights'),
              numeric: true,
              cell: (booster) => formatNumber(locale, booster.flights),
            },
            {
              key: 'landings',
              header: t('launches.boosters.landings'),
              numeric: true,
              cell: (booster) =>
                booster.landings === undefined ? '—' : formatNumber(locale, booster.landings),
            },
            {
              key: 'first',
              header: t('launches.boosters.firstFlight'),
              cell: (booster) =>
                booster.first_flight_at === undefined
                  ? '—'
                  : formatDate(locale, booster.first_flight_at),
            },
            {
              key: 'status',
              header: t('common.status'),
              cell: (booster) => booster.status?.name ?? '—',
            },
          ]}
        />
      )}
    </DataRegion>
  );
}

function Pads() {
  const { t } = useTranslation();
  const locale = useLocale();
  const theme = useChartTheme();
  const query = useQuery(launchPadsQuery(locale, { limit: 10 }));
  const pads = useMemo(() => [...(query.data?.items ?? [])].reverse(), [query.data]);
  const option = useMemo<ChartOption>(() => {
    const axis = axisStyle(theme);
    return {
      ...baseOption(theme),
      grid: { left: 8, right: 48, top: 8, bottom: 8, containLabel: true },
      tooltip: { ...baseOption(theme).tooltip, trigger: 'axis', axisPointer: { type: 'shadow' } },
      xAxis: { type: 'value', ...axis },
      yAxis: {
        type: 'category',
        data: pads.map((pad) => `${pad.pad.name} · ${pad.pad.location?.split(',')[0] ?? ''}`),
        ...axis,
        axisLabel: { ...axis.axisLabel, width: 220, overflow: 'truncate' },
        splitLine: { show: false },
      },
      series: [
        {
          type: 'bar',
          name: t('common.attempts'),
          data: pads.map((pad) => pad.attempts),
          barWidth: 10,
          itemStyle: { color: theme.warm, borderRadius: [0, 4, 4, 0] },
          label: { show: true, position: 'right', color: theme.ink, fontSize: 11 },
        },
      ],
    };
  }, [theme, pads, t]);

  return (
    <DataRegion query={query} minHeight={500}>
      {(data) => (
        <ChartFigure
          title={t('launches.pads.title')}
          description={t('launches.pads.description')}
          option={option}
          height={380}
          sources={['launch-library']}
          rows={data.items}
          rowKey={(pad) => String(pad.pad.id)}
          columns={[
            { key: 'pad', header: t('common.name'), cell: (pad) => pad.pad.name },
            { key: 'site', header: t('common.location'), cell: (pad) => pad.pad.location ?? '—' },
            {
              key: 'attempts',
              header: t('common.attempts'),
              numeric: true,
              cell: (pad) => formatNumber(locale, pad.attempts),
            },
            {
              key: 'successes',
              header: t('common.successes'),
              numeric: true,
              cell: (pad) => formatNumber(locale, pad.successes),
            },
          ]}
        />
      )}
    </DataRegion>
  );
}

function Schedule() {
  const { t } = useTranslation();
  const locale = useLocale();
  const now = hoursAgo(0);
  const upcoming = useQuery(launchesQuery(locale, { from: now, sort: 'net', size: 8 }));
  const recent = useQuery(launchesQuery(locale, { to: now, sort: '-net', size: 8 }));

  return (
    <div className="flex flex-col gap-14">
      <LaunchTable title={t('launches.upcoming')} query={upcoming} />
      <LaunchTable title={t('launches.recent')} query={recent} />
    </div>
  );
}

export function LaunchesPage() {
  const { t } = useTranslation();
  useDocumentTitle(t('pages.launches.title'));

  return (
    <PageLayout title={t('pages.launches.title')} lede={t('pages.launches.lede')}>
      <Section id="launch-facts" title={t('launches.facts')}>
        <ModuleFacts module="launches" />
      </Section>
      <Section
        id="launch-cadence"
        title={t('launches.cadence.title')}
        lede={t('launches.cadence.lede')}
      >
        <Cadence />
      </Section>
      <Section
        id="launch-success"
        title={t('launches.success.title')}
        lede={t('launches.success.lede')}
      >
        <Success />
      </Section>
      <Section
        id="launch-reusability"
        title={t('launches.reusability.title')}
        lede={t('launches.reusability.lede')}
      >
        <Reusability />
      </Section>
      <Section
        id="launch-boosters"
        title={t('launches.boosters.title')}
        lede={t('launches.boosters.lede')}
      >
        <Boosters />
      </Section>
      <Section id="launch-pads" title={t('launches.pads.title')} lede={t('launches.pads.lede')}>
        <Pads />
      </Section>
      <Section id="launch-schedule" title={t('launches.schedule')}>
        <Schedule />
      </Section>
    </PageLayout>
  );
}
