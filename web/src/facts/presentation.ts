export type Accent = 'warm' | 'cool';

export type FigureFormat = 'integer' | 'percent' | 'decimal1' | 'decimal2' | 'year' | 'text';

export type FigureUnit = 'km' | 'kms' | 'm' | 'ld' | 'kp' | 'days' | 'ly';

export type FigureSpec =
  | { readonly param: string; readonly format: FigureFormat; readonly unit?: FigureUnit }
  | { readonly range: readonly [string, string]; readonly unit: FigureUnit };

export type ScaleSpec =
  | { readonly kind: 'lunar'; readonly param: string }
  | { readonly kind: 'percent'; readonly param: string }
  | { readonly kind: 'kp'; readonly param: string }
  | { readonly kind: 'flare'; readonly param: string }
  | { readonly kind: 'timeline'; readonly param: string; readonly from: number }
  | { readonly kind: 'span'; readonly first: string; readonly last: string }
  | { readonly kind: 'skytree'; readonly min: string; readonly max: string }
  | { readonly kind: 'multiple'; readonly param: string; readonly reference: 'shinkansen' | 'fuji' }
  | { readonly kind: 'earthDistance'; readonly param: string }
  | { readonly kind: 'ratio'; readonly param: string; readonly year: string };

export interface FactPresentation {
  readonly figure: FigureSpec;
  readonly scale?: ScaleSpec;
}

export const MODULE_ACCENTS: Readonly<Record<string, Accent>> = {
  launches: 'warm',
  'space-weather': 'warm',
  agencies: 'warm',
  'near-earth': 'cool',
  orbits: 'cool',
  sources: 'cool',
  exoplanets: 'cool',
};

export const PRESENTATIONS: Readonly<Record<string, FactPresentation>> = {
  'agencies.launch_total': { figure: { param: 'attempts', format: 'integer' } },
  'agencies.success_rate': {
    figure: { param: 'rate', format: 'percent' },
    scale: { kind: 'percent', param: 'rate' },
  },
  'agencies.first_launch': {
    figure: { param: 'date', format: 'year' },
    scale: { kind: 'timeline', param: 'date', from: 1950 },
  },
  'agencies.busiest_year': { figure: { param: 'attempts', format: 'integer' } },
  'agencies.oldest': {
    figure: { param: 'founded', format: 'year' },
    scale: { kind: 'timeline', param: 'founded', from: 1870 },
  },
  'launches.year_to_date': {
    figure: { param: 'launches', format: 'integer' },
    scale: { kind: 'ratio', param: 'ratio', year: 'year' },
  },
  'launches.record_year': { figure: { param: 'attempts', format: 'integer' } },
  'launches.program_year': { figure: { param: 'attempts', format: 'integer' } },
  'launches.success_streak': { figure: { param: 'streak', format: 'integer' } },
  'launches.busiest_pad': { figure: { param: 'attempts', format: 'integer' } },
  'launches.site_country_share': {
    figure: { param: 'share', format: 'percent' },
    scale: { kind: 'percent', param: 'share' },
  },
  'launches.most_flown_booster': { figure: { param: 'flights', format: 'integer' } },
  'launches.landing_success_year': {
    figure: { param: 'rate', format: 'percent' },
    scale: { kind: 'percent', param: 'rate' },
  },
  'launches.reflown_share': {
    figure: { param: 'share', format: 'percent' },
    scale: { kind: 'percent', param: 'share' },
  },
  'launches.fastest_turnaround': { figure: { param: 'days', format: 'decimal1', unit: 'days' } },
  'exoplanets.confirmed_total': { figure: { param: 'total', format: 'integer' } },
  'exoplanets.record_year': { figure: { param: 'planets', format: 'integer' } },
  'exoplanets.nearest': { figure: { param: 'light_years', format: 'decimal1', unit: 'ly' } },
  'exoplanets.transit_share': {
    figure: { param: 'share', format: 'percent' },
    scale: { kind: 'percent', param: 'share' },
  },
  'exoplanets.earth_sized_temperate': { figure: { param: 'planets', format: 'integer' } },
  'near-earth.closest_this_week': {
    figure: { param: 'distance', format: 'decimal1', unit: 'ld' },
    scale: { kind: 'lunar', param: 'distance' },
  },
  'near-earth.inside_moon_orbit_year': { figure: { param: 'flybys', format: 'integer' } },
  'near-earth.largest_next_year': {
    figure: { range: ['size_min', 'size_max'], unit: 'm' },
    scale: { kind: 'skytree', min: 'size_min', max: 'size_max' },
  },
  'near-earth.fastest_next_year': {
    figure: { param: 'speed', format: 'decimal1', unit: 'kms' },
    scale: { kind: 'multiple', param: 'times', reference: 'shinkansen' },
  },
  'near-earth.closest_this_century': {
    figure: { param: 'distance', format: 'integer', unit: 'km' },
    scale: { kind: 'earthDistance', param: 'distance' },
  },
  'near-earth.sentry_watchlist': { figure: { param: 'objects', format: 'integer' } },
  'orbits.objects_in_orbit': { figure: { param: 'objects', format: 'integer' } },
  'orbits.debris_share': {
    figure: { param: 'share', format: 'percent' },
    scale: { kind: 'percent', param: 'share' },
  },
  'orbits.country_payloads': {
    figure: { param: 'payloads', format: 'integer' },
    scale: { kind: 'percent', param: 'share' },
  },
  'orbits.oldest_in_orbit': {
    figure: { param: 'date', format: 'year' },
    scale: { kind: 'timeline', param: 'date', from: 1957 },
  },
  'orbits.reentries_year': { figure: { param: 'objects', format: 'integer' } },
  'orbits.iss_altitude': {
    figure: { param: 'altitude', format: 'integer', unit: 'km' },
    scale: { kind: 'multiple', param: 'fujis', reference: 'fuji' },
  },
  'space-weather.strongest_flare_week': {
    figure: { param: 'flare_class', format: 'text' },
    scale: { kind: 'flare', param: 'flare_class' },
  },
  'space-weather.flares_week': { figure: { param: 'flares', format: 'integer' } },
  'space-weather.kp_peak_week': {
    figure: { param: 'kp', format: 'decimal2', unit: 'kp' },
    scale: { kind: 'kp', param: 'kp' },
  },
  'space-weather.fastest_wind_day': {
    figure: { param: 'speed', format: 'integer', unit: 'kms' },
  },
  'space-weather.alerts_week': { figure: { param: 'alerts', format: 'integer' } },
  'sources.launch_records': { figure: { param: 'launches', format: 'integer' } },
  'sources.catalog_size': { figure: { param: 'objects', format: 'integer' } },
  'sources.close_approach_span': {
    figure: { param: 'approaches', format: 'integer' },
    scale: { kind: 'span', first: 'first', last: 'last' },
  },
};

export function presentationFor(templateKey: string): FactPresentation | undefined {
  return PRESENTATIONS[templateKey];
}

export function accentFor(module: string): Accent {
  return MODULE_ACCENTS[module] ?? 'cool';
}
