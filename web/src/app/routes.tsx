import type { RouteObject } from 'react-router';
import { HomePage } from '../pages/HomePage';
import { NotFoundPage } from '../pages/NotFoundPage';
import { AppRoot } from './AppRoot';
import { LocaleLayout } from './LocaleLayout';
import { LocaleRedirect } from './LocaleRedirect';
import { RouteError } from './RouteError';
import {
  agenciesQuery,
  agencyQuery,
  factsQuery,
  overviewQuery,
  sourcesQuery,
  spaceWeatherNowQuery,
} from '../api/queries';
import { prefetch, prefetching } from './prefetch';

const moduleFacts = (module: string) =>
  prefetching((locale) => {
    prefetch(factsQuery(locale, { limit: 3, module }));
  });

export const routes: RouteObject[] = [
  {
    element: <AppRoot />,
    errorElement: <RouteError />,
    children: [
      { path: '/', element: <LocaleRedirect /> },
      {
        path: ':locale',
        element: <LocaleLayout />,
        children: [
          {
            index: true,
            element: <HomePage />,
            loader: prefetching((locale) => {
              prefetch(overviewQuery(locale));
              prefetch(factsQuery(locale, { limit: 6 }));
            }),
          },
          {
            path: 'launches',
            loader: moduleFacts('launches'),
            lazy: async () => ({ Component: (await import('../pages/LaunchesPage')).LaunchesPage }),
          },
          {
            path: 'near-earth',
            loader: moduleFacts('near-earth'),
            lazy: async () => ({
              Component: (await import('../pages/NearEarthPage')).NearEarthPage,
            }),
          },
          {
            path: 'sun',
            loader: prefetching((locale) => {
              prefetch(spaceWeatherNowQuery(locale));
              prefetch(factsQuery(locale, { limit: 3, module: 'space-weather' }));
            }),
            lazy: async () => ({ Component: (await import('../pages/SunPage')).SunPage }),
          },
          {
            path: 'exoplanets',
            loader: moduleFacts('exoplanets'),
            lazy: async () => ({
              Component: (await import('../pages/ExoplanetsPage')).ExoplanetsPage,
            }),
          },
          {
            path: 'agencies',
            loader: prefetching((locale) => {
              prefetch(agenciesQuery(locale, { has_launches: true, sort: '-launches', size: 60 }));
            }),
            lazy: async () => ({ Component: (await import('../pages/AgenciesPage')).AgenciesPage }),
          },
          {
            path: 'agencies/:key',
            loader: prefetching((locale, params) => {
              prefetch(agencyQuery(locale, params.key ?? ''));
            }),
            lazy: async () => ({ Component: (await import('../pages/AgencyPage')).AgencyPage }),
          },
          {
            path: 'sources',
            loader: prefetching((locale) => {
              prefetch(sourcesQuery(locale));
            }),
            lazy: async () => ({ Component: (await import('../pages/SourcesPage')).SourcesPage }),
          },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
  },
];
