import { QueryClientProvider } from '@tanstack/react-query';
import { useEffect } from 'react';
import { Outlet } from 'react-router';
import { dataLinkState, subscribeDataLink } from '../api/dataLink';
import { queryClient as client, retryStalledQueries } from '../api/queryClient';

export function AppRoot() {
  useEffect(() => {
    let second = 0;
    const first = requestAnimationFrame(() => {
      second = requestAnimationFrame(() => {
        void import('../styles/fonts');
      });
    });
    return () => {
      cancelAnimationFrame(first);
      cancelAnimationFrame(second);
    };
  }, []);

  useEffect(() => {
    let previous = dataLinkState().status;
    return subscribeDataLink(() => {
      const { status } = dataLinkState();
      if (status === 'connected' && (previous === 'waking' || previous === 'offline')) {
        void retryStalledQueries(client);
      }
      previous = status;
    });
  }, []);

  return (
    <QueryClientProvider client={client}>
      <Outlet />
    </QueryClientProvider>
  );
}
