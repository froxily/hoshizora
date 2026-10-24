import { queryOptions } from '@tanstack/react-query';
import type { Locale } from '../i18n/locales';
import { api, load, requestOptions } from './client';
import type { components, paths } from './schema';

export type Schemas = components['schemas'];
export type Overview = Schemas['Overview'];
export type Fact = Schemas['Fact'];
export type FactDetail = Schemas['FactDetail'];

type QueryOf<P extends keyof paths> = NonNullable<paths[P]['get']['parameters']['query']>;

export type GroupBy = NonNullable<QueryOf<'/api/v1/stats/launches/cadence'>['group_by']>;

const HOUR_MS = 3_600_000;

export function hoursAgo(hours: number, now: number = Date.now()): string {
  const hour = Math.floor(now / HOUR_MS) * HOUR_MS;
  return new Date(hour - hours * HOUR_MS).toISOString().replace('.000Z', 'Z');
}

function apiQuery<T>(key: readonly unknown[], fetcher: (signal: AbortSignal) => Promise<T>) {
  return queryOptions({ queryKey: key, queryFn: ({ signal }) => fetcher(signal) });
}

export function overviewQuery(locale: Locale) {
  return apiQuery(['overview', locale], (signal) =>
    load(() => api.GET('/api/v1/stats/overview', requestOptions(locale, signal))),
  );
}

interface FactFilter {
  readonly module?: string;
  readonly entityType?: string;
  readonly entityKey?: string;
  readonly limit?: number;
}

export function factsQuery(locale: Locale, filter: FactFilter = {}) {
  return queryOptions({
    queryKey: ['facts', locale, filter],
    queryFn: ({ signal }) =>
      load(() =>
        api.GET('/api/v1/facts', {
          ...requestOptions(locale, signal),
          params: {
            query: {
              ...(filter.module === undefined ? {} : { module: filter.module }),
              ...(filter.entityType === undefined ? {} : { entity_type: filter.entityType }),
              ...(filter.entityKey === undefined ? {} : { entity_key: filter.entityKey }),
              ...(filter.limit === undefined ? {} : { limit: filter.limit }),
            },
          },
        }),
      ),
    select: (facts) => facts.items,
  });
}

export function factQuery(locale: Locale, id: number) {
  return apiQuery(['fact', locale, id], (signal) =>
    load(() =>
      api.GET('/api/v1/facts/{id}', {
        ...requestOptions(locale, signal),
        params: { path: { id } },
      }),
    ),
  );
}

export function launchCadenceQuery(
  locale: Locale,
  query: QueryOf<'/api/v1/stats/launches/cadence'>,
) {
  return apiQuery(['launch-cadence', locale, query], (signal) =>
    load(() =>
      api.GET('/api/v1/stats/launches/cadence', {
        ...requestOptions(locale, signal),
        params: { query },
      }),
    ),
  );
}

export function launchSuccessQuery(
  locale: Locale,
  query: QueryOf<'/api/v1/stats/launches/success'>,
) {
  return apiQuery(['launch-success', locale, query], (signal) =>
    load(() =>
      api.GET('/api/v1/stats/launches/success', {
        ...requestOptions(locale, signal),
        params: { query },
      }),
    ),
  );
}

export function launchPadsQuery(locale: Locale, query: QueryOf<'/api/v1/stats/launches/pads'>) {
  return apiQuery(['launch-pads', locale, query], (signal) =>
    load(() =>
      api.GET('/api/v1/stats/launches/pads', {
        ...requestOptions(locale, signal),
        params: { query },
      }),
    ),
  );
}

export function launchReusabilityQuery(
  locale: Locale,
  query: QueryOf<'/api/v1/stats/launches/reusability'>,
) {
  return apiQuery(['launch-reusability', locale, query], (signal) =>
    load(() =>
      api.GET('/api/v1/stats/launches/reusability', {
        ...requestOptions(locale, signal),
        params: { query },
      }),
    ),
  );
}

export function launchBoostersQuery(
  locale: Locale,
  query: QueryOf<'/api/v1/stats/launches/boosters'>,
) {
  return apiQuery(['launch-boosters', locale, query], (signal) =>
    load(() =>
      api.GET('/api/v1/stats/launches/boosters', {
        ...requestOptions(locale, signal),
        params: { query },
      }),
    ),
  );
}

export function launchesQuery(locale: Locale, query: QueryOf<'/api/v1/launches'>) {
  return apiQuery(['launches', locale, query], (signal) =>
    load(() =>
      api.GET('/api/v1/launches', { ...requestOptions(locale, signal), params: { query } }),
    ),
  );
}

export function closeApproachesQuery(locale: Locale, query: QueryOf<'/api/v1/close-approaches'>) {
  return apiQuery(['close-approaches', locale, query], (signal) =>
    load(() =>
      api.GET('/api/v1/close-approaches', { ...requestOptions(locale, signal), params: { query } }),
    ),
  );
}

export function closeApproachMonthlyQuery(
  locale: Locale,
  query: QueryOf<'/api/v1/stats/close-approaches/monthly'>,
) {
  return apiQuery(['close-approach-monthly', locale, query], (signal) =>
    load(() =>
      api.GET('/api/v1/stats/close-approaches/monthly', {
        ...requestOptions(locale, signal),
        params: { query },
      }),
    ),
  );
}

export function impactRisksQuery(locale: Locale, query: QueryOf<'/api/v1/impact-risks'>) {
  return apiQuery(['impact-risks', locale, query], (signal) =>
    load(() =>
      api.GET('/api/v1/impact-risks', { ...requestOptions(locale, signal), params: { query } }),
    ),
  );
}

export function exoplanetsQuery(locale: Locale, query: QueryOf<'/api/v1/exoplanets'>) {
  return apiQuery(['exoplanets', locale, query], (signal) =>
    load(() =>
      api.GET('/api/v1/exoplanets', { ...requestOptions(locale, signal), params: { query } }),
    ),
  );
}

export function exoplanetDiscoveriesQuery(
  locale: Locale,
  query: QueryOf<'/api/v1/stats/exoplanets/discoveries'>,
) {
  return apiQuery(['exoplanet-discoveries', locale, query], (signal) =>
    load(() =>
      api.GET('/api/v1/stats/exoplanets/discoveries', {
        ...requestOptions(locale, signal),
        params: { query },
      }),
    ),
  );
}

export function exoplanetSizeOrbitQuery(locale: Locale) {
  return apiQuery(['exoplanet-size-orbit', locale], (signal) =>
    load(() => api.GET('/api/v1/stats/exoplanets/size-orbit', requestOptions(locale, signal))),
  );
}

export function spaceWeatherNowQuery(locale: Locale) {
  return apiQuery(['space-weather-now', locale], (signal) =>
    load(() => api.GET('/api/v1/space-weather/now', requestOptions(locale, signal))),
  );
}

export function kpQuery(locale: Locale, query: QueryOf<'/api/v1/space-weather/kp'>) {
  return apiQuery(['kp', locale, query], (signal) =>
    load(() =>
      api.GET('/api/v1/space-weather/kp', { ...requestOptions(locale, signal), params: { query } }),
    ),
  );
}

export function flaresQuery(locale: Locale, query: QueryOf<'/api/v1/space-weather/flares'>) {
  return apiQuery(['flares', locale, query], (signal) =>
    load(() =>
      api.GET('/api/v1/space-weather/flares', {
        ...requestOptions(locale, signal),
        params: { query },
      }),
    ),
  );
}

export function solarWindQuery(locale: Locale, query: QueryOf<'/api/v1/space-weather/solar-wind'>) {
  return apiQuery(['solar-wind', locale, query], (signal) =>
    load(() =>
      api.GET('/api/v1/space-weather/solar-wind', {
        ...requestOptions(locale, signal),
        params: { query },
      }),
    ),
  );
}

export function auroraQuery(locale: Locale, query: QueryOf<'/api/v1/space-weather/aurora'>) {
  return apiQuery(['aurora', locale, query], (signal) =>
    load(() =>
      api.GET('/api/v1/space-weather/aurora', {
        ...requestOptions(locale, signal),
        params: { query },
      }),
    ),
  );
}

export function agenciesQuery(locale: Locale, query: QueryOf<'/api/v1/agencies'>) {
  return apiQuery(['agencies', locale, query], (signal) =>
    load(() =>
      api.GET('/api/v1/agencies', { ...requestOptions(locale, signal), params: { query } }),
    ),
  );
}

export function agencyQuery(locale: Locale, key: string) {
  return apiQuery(['agency', locale, key], (signal) =>
    load(() =>
      api.GET('/api/v1/agencies/{key}', {
        ...requestOptions(locale, signal),
        params: { path: { key } },
      }),
    ),
  );
}

export function sourcesQuery(locale: Locale) {
  return apiQuery(['sources', locale], (signal) =>
    load(() =>
      api.GET('/api/v1/meta/sources', {
        ...requestOptions(locale, signal),
        params: { query: { size: 50 } },
      }),
    ),
  );
}
