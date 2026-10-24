import type { QueryFunction, QueryKey } from '@tanstack/react-query';
import type { LoaderFunctionArgs, Params } from 'react-router';
import { queryClient } from '../api/queryClient';
import { isLocale, type Locale } from '../i18n/locales';

interface Prefetchable {
  readonly queryKey: QueryKey;
  readonly queryFn?: unknown;
}

export function prefetch(options: Prefetchable): void {
  queryClient
    .query({ queryKey: options.queryKey, queryFn: options.queryFn as QueryFunction })
    .catch(() => undefined);
}

export function prefetching(plan: (locale: Locale, params: Params) => void) {
  return ({ params }: LoaderFunctionArgs): null => {
    if (isLocale(params.locale)) {
      plan(params.locale, params);
    }
    return null;
  };
}
