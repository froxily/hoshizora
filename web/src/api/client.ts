import createClient from 'openapi-fetch';
import type { Locale } from '../i18n/locales';
import { markConnected, markWaking, SLOW_RESPONSE_MS } from './dataLink';
import type { components, paths } from './schema';

export type Problem = components['schemas']['Problem'];

const REQUEST_TIMEOUT_MS = 25_000;
const WAKING_STATUSES = new Set([502, 503, 504]);

export class ApiError extends Error {
  readonly status: number;
  readonly problem: Problem | null;

  constructor(status: number, problem: Problem | null) {
    super(`API responded ${String(status)}`);
    this.name = 'ApiError';
    this.status = status;
    this.problem = problem;
  }
}

export class DataLinkError extends Error {
  constructor(cause: unknown) {
    super('The data link is not answering', { cause });
    this.name = 'DataLinkError';
  }
}

export const api = createClient<paths>({
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? '',
  fetch: (request) => globalThis.fetch(request),
});

function isProblem(value: unknown): value is Problem {
  return typeof value === 'object' && value !== null && 'status' in value;
}

function isJson(response: Response): boolean {
  return response.headers.get('content-type')?.includes('json') ?? false;
}

export function isDataLinkError(error: unknown): error is DataLinkError {
  return error instanceof DataLinkError;
}

interface Outcome<T> {
  readonly data?: T;
  readonly error?: unknown;
  readonly response: Response;
}

export function requestOptions(locale: Locale, signal: AbortSignal) {
  return {
    headers: { 'Accept-Language': locale },
    signal: AbortSignal.any([signal, AbortSignal.timeout(REQUEST_TIMEOUT_MS)]),
  };
}

export async function load<T>(call: () => Promise<Outcome<T>>): Promise<T> {
  const slow = setTimeout(markWaking, SLOW_RESPONSE_MS);
  try {
    const { data, error, response } = await call();
    if (WAKING_STATUSES.has(response.status) || !isJson(response)) {
      markWaking();
      throw new DataLinkError(response.status);
    }
    markConnected();
    if (data === undefined) {
      throw new ApiError(response.status, isProblem(error) ? error : null);
    }
    return data;
  } catch (error) {
    if (error instanceof ApiError || error instanceof DataLinkError) {
      throw error;
    }
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error;
    }
    markWaking();
    throw new DataLinkError(error);
  } finally {
    clearTimeout(slow);
  }
}
