import { useQuery } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { useDataLink } from '../../api/dataLink';
import { overviewQuery, type Overview } from '../../api/queries';
import { DataLinkPanel, ScanLine } from '../../components/DataLink';
import { SourceNote } from '../../components/SourceNote';
import { countdown, formatDate, formatDecimal, formatNumber, pad2 } from '../../format/format';
import type { Locale } from '../../i18n/locales';
import { useLocale } from '../../i18n/useLocale';
import { useNow } from '../../time/now';

interface CellProps {
  readonly label: string;
  readonly ready: boolean;
  readonly children?: ReactNode;
}

function Cell({ label, ready, children }: CellProps) {
  return (
    <div className="relative flex min-w-0 flex-col gap-2 border-t border-hairline-strong pt-4">
      <p className="hz-label">{label}</p>
      {ready ? (
        <div className="hz-fade flex flex-1 flex-col gap-2">{children}</div>
      ) : (
        <div className="relative flex flex-1 flex-col gap-3 overflow-hidden pt-2" aria-hidden>
          <ScanLine />
          <span className="mt-2 h-8 w-32 rounded-sm bg-surface" />
          <span className="h-3 w-40 rounded-sm bg-surface" />
        </div>
      )}
    </div>
  );
}

function Figure({ value, unit }: { value: string; unit?: string }) {
  return (
    <p className="font-display text-figure leading-none font-extralight text-ink">
      {value}
      {unit !== undefined && <span className="ml-2 text-lg font-light text-ink-muted">{unit}</span>}
    </p>
  );
}

function Countdown({ net }: { net: string }) {
  const { t } = useTranslation();
  const now = useNow();
  const parts = countdown(net, now);
  const clock = `${pad2(parts.hours)}:${pad2(parts.minutes)}:${pad2(parts.seconds)}`;
  return (
    <p className="flex items-baseline gap-2 whitespace-nowrap">
      <span className="text-sm text-ink-muted">
        {t(parts.past ? 'countdown.after' : 'countdown.before')}
      </span>
      <span className="font-display text-2xl leading-none font-light text-ink tabular-nums">
        {parts.days > 0 && `${t('countdown.days', { days: parts.days })} `}
        {clock}
      </span>
    </p>
  );
}

function sizeMeters(locale: Locale, km: number): string {
  return formatNumber(locale, km * 1_000, { maximumSignificantDigits: 2 });
}

interface OverviewProps {
  readonly overview: Overview;
  readonly locale: Locale;
}

function NextLaunch({ overview }: OverviewProps) {
  const { t } = useTranslation();
  const launch = overview.next_launch;
  if (launch?.net === undefined) {
    return <p className="text-sm text-ink-muted">{t('home.ticker.noLaunch')}</p>;
  }
  return (
    <>
      <Countdown net={launch.net} />
      <p lang={launch.name_lang} className="line-clamp-2 text-sm text-ink">
        {launch.name}
      </p>
      <p className="truncate text-xs text-ink-muted">
        {[launch.provider?.name, launch.pad?.location].filter(Boolean).join(' · ')}
      </p>
      <SourceNote sources={['launch-library']} asOf={overview.as_of} />
    </>
  );
}

function Kp({ overview, locale }: OverviewProps) {
  const { t } = useTranslation();
  const kp = overview.kp;
  if (kp === undefined) {
    return <p className="text-sm text-ink-muted">{t('home.ticker.noKp')}</p>;
  }
  return (
    <>
      <Figure value={formatDecimal(locale, kp.kp, 1)} unit={t('units.kp')} />
      <p className="text-sm text-ink">{kp.g_scale.name}</p>
      <SourceNote sources={['swpc']} asOf={kp.observed_at} />
    </>
  );
}

function Closest({ overview, locale }: OverviewProps) {
  const { t } = useTranslation();
  const approach = overview.closest_approach_this_week;
  if (approach === undefined) {
    return <p className="text-sm text-ink-muted">{t('home.ticker.noClosest')}</p>;
  }
  const minKm = approach.size.estimated_min_km;
  const maxKm = approach.size.estimated_max_km;
  return (
    <>
      <p className="font-display text-figure leading-none font-extralight text-ink">
        {formatDecimal(locale, approach.dist_ld, 2)}
        <abbr
          title={t('units.ldLong')}
          className="ml-2 text-lg font-light text-ink-muted no-underline"
        >
          {t('units.ld')}
        </abbr>
      </p>
      <p className="text-sm text-ink">
        {approach.fullname?.trim() ?? approach.designation} ·{' '}
        {formatDate(locale, approach.approach_utc ?? approach.approach_tdb)}
      </p>
      {minKm !== undefined && maxKm !== undefined && (
        <p className="text-xs text-ink-muted">
          {t('home.ticker.sizeRange', {
            min: sizeMeters(locale, minKm),
            max: sizeMeters(locale, maxKm),
          })}
        </p>
      )}
      <SourceNote sources={['jpl']} asOf={overview.as_of} />
    </>
  );
}

function LaunchesThisYear({ overview, locale }: OverviewProps) {
  const { t } = useTranslation();
  const year = overview.launches_this_year;
  return (
    <>
      <Figure value={formatNumber(locale, year.attempts)} />
      <p className="text-sm text-ink-muted">
        {t('home.ticker.lastYear', { count: formatNumber(locale, year.same_period_last_year) })}
      </p>
      <SourceNote sources={['launch-library']} asOf={overview.as_of} />
    </>
  );
}

export function Ticker() {
  const { t } = useTranslation();
  const locale = useLocale();
  const link = useDataLink();
  const query = useQuery(overviewQuery(locale));
  const overview = query.data;
  const stalled =
    overview === undefined &&
    (link.status === 'waking' || link.status === 'offline' || query.isError);
  const year = overview?.launches_this_year.year ?? new Date().getUTCFullYear();

  return (
    <section aria-labelledby="ticker-title" className="space-y-5">
      <h2 id="ticker-title" className="hz-label text-amber">
        {t('home.ticker.title')}
      </h2>
      {stalled && (
        <div className="max-w-xl">
          <DataLinkPanel />
        </div>
      )}
      <div className="grid gap-x-8 gap-y-6 sm:grid-cols-2">
        <Cell label={t('home.ticker.nextLaunch')} ready={overview !== undefined}>
          {overview && <NextLaunch overview={overview} locale={locale} />}
        </Cell>
        <Cell label={t('home.ticker.kp')} ready={overview !== undefined}>
          {overview && <Kp overview={overview} locale={locale} />}
        </Cell>
        <Cell label={t('home.ticker.closest')} ready={overview !== undefined}>
          {overview && <Closest overview={overview} locale={locale} />}
        </Cell>
        <Cell label={t('home.ticker.launchesYear', { year })} ready={overview !== undefined}>
          {overview && <LaunchesThisYear overview={overview} locale={locale} />}
        </Cell>
      </div>
    </section>
  );
}
