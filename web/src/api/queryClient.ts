import { QueryClient } from '@tanstack/react-query';
import { isDataLinkError } from './client';
import { dataLinkState } from './dataLink';

const WAKING_RETRY_CAP_MS = 10_000;
const OFFLINE_RETRY_MS = 30_000;

export function retryDelay(attempt: number): number {
  if (dataLinkState().status === 'offline') {
    return OFFLINE_RETRY_MS;
  }
  return Math.min(1_000 * 2 ** attempt, WAKING_RETRY_CAP_MS);
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60_000,
        gcTime: 30 * 60_000,
        refetchOnWindowFocus: false,
        retry: (_count, error) => isDataLinkError(error),
        retryDelay,
      },
    },
  });
}

export function retryStalledQueries(client: QueryClient): Promise<void> {
  return client.refetchQueries({
    predicate: (query) => query.state.fetchFailureCount > 0 || query.state.status === 'error',
  });
}

export const queryClient = createQueryClient();
