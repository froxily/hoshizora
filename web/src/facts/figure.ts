import { formatCompact, formatNumber } from '../format/format';
import type { Locale } from '../i18n/locales';
import { numberParam, textParam, yearParam, type Params } from './params';
import type { FigureSpec, FigureUnit } from './presentation';

const JA_COMPACT_FROM = 10_000;

export interface Figure {
  readonly value: string;
  readonly unit?: FigureUnit;
}

function integer(locale: Locale, value: number): string {
  return locale === 'ja' && Math.abs(value) >= JA_COMPACT_FROM
    ? formatCompact(locale, value)
    : formatNumber(locale, Math.round(value));
}

function formatValue(locale: Locale, spec: FigureSpec, params: Params): string | undefined {
  if ('range' in spec) {
    const min = numberParam(params, spec.range[0]);
    const max = numberParam(params, spec.range[1]);
    if (min === undefined || max === undefined) {
      return undefined;
    }
    const digits = { maximumSignificantDigits: 2 };
    return `${formatNumber(locale, min, digits)}–${formatNumber(locale, max, digits)}`;
  }
  switch (spec.format) {
    case 'text':
      return textParam(params, spec.param);
    case 'year': {
      const year = yearParam(params, spec.param);
      return year === undefined ? undefined : String(year);
    }
    default: {
      const value = numberParam(params, spec.param);
      if (value === undefined) {
        return undefined;
      }
      switch (spec.format) {
        case 'integer':
          return integer(locale, value);
        case 'percent':
          return formatNumber(locale, value, { style: 'percent', maximumFractionDigits: 0 });
        case 'decimal1':
          return formatNumber(locale, value, { maximumFractionDigits: 1 });
        case 'decimal2':
          return formatNumber(locale, value, { maximumFractionDigits: 2 });
      }
    }
  }
}

export function figureFor(locale: Locale, spec: FigureSpec, params: Params): Figure | undefined {
  const value = formatValue(locale, spec, params);
  if (value === undefined) {
    return undefined;
  }
  return spec.unit === undefined ? { value } : { value, unit: spec.unit };
}
