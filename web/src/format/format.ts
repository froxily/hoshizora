import type { Locale } from '../i18n/locales';

const LOCALE_TAGS: Record<Locale, string> = { en: 'en-US', ja: 'ja-JP' };

const numberFormats = new Map<string, Intl.NumberFormat>();
const dateFormats = new Map<string, Intl.DateTimeFormat>();

function numberFormat(locale: Locale, options: Intl.NumberFormatOptions): Intl.NumberFormat {
  const key = `${locale}|${JSON.stringify(options)}`;
  let format = numberFormats.get(key);
  if (format === undefined) {
    format = new Intl.NumberFormat(LOCALE_TAGS[locale], options);
    numberFormats.set(key, format);
  }
  return format;
}

function dateFormat(locale: Locale, options: Intl.DateTimeFormatOptions): Intl.DateTimeFormat {
  const key = `${locale}|${JSON.stringify(options)}`;
  let format = dateFormats.get(key);
  if (format === undefined) {
    format = new Intl.DateTimeFormat(LOCALE_TAGS[locale], options);
    dateFormats.set(key, format);
  }
  return format;
}

export function formatNumber(
  locale: Locale,
  value: number,
  options: Intl.NumberFormatOptions = {},
): string {
  return numberFormat(locale, options).format(value);
}

export function formatDecimal(locale: Locale, value: number, digits: number): string {
  return formatNumber(locale, value, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

export function formatCompact(locale: Locale, value: number): string {
  return formatNumber(locale, value, { notation: 'compact', maximumFractionDigits: 1 });
}

export function formatDate(locale: Locale, instant: string | Date): string {
  return dateFormat(locale, { dateStyle: 'long' }).format(new Date(instant));
}

export function formatDateTime(locale: Locale, instant: string | Date): string {
  return dateFormat(locale, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(new Date(instant));
}

export interface Countdown {
  readonly past: boolean;
  readonly days: number;
  readonly hours: number;
  readonly minutes: number;
  readonly seconds: number;
}

export function countdown(target: string | Date, now: number): Countdown {
  const delta = new Date(target).getTime() - now;
  const total = Math.floor(Math.abs(delta) / 1_000);
  return {
    past: delta < 0,
    days: Math.floor(total / 86_400),
    hours: Math.floor((total % 86_400) / 3_600),
    minutes: Math.floor((total % 3_600) / 60),
    seconds: total % 60,
  };
}

export function pad2(value: number): string {
  return String(value).padStart(2, '0');
}
