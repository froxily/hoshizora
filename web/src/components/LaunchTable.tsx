import type { UseQueryResult } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import type { Schemas } from '../api/queries';
import { formatDateTime } from '../format/format';
import { useLocale } from '../i18n/useLocale';
import { DataRegion } from './DataRegion';
import { DataTable, type Column } from './DataTable';

type Launch = Schemas['LaunchSummary'];

interface LaunchListProps {
  readonly title: string;
  readonly launches: readonly Launch[];
}

export function LaunchList({ title, launches }: LaunchListProps) {
  const { t } = useTranslation();
  const locale = useLocale();
  const columns: Column<Launch>[] = [
    {
      key: 'net',
      header: t('common.date'),
      cell: (launch) =>
        launch.net === undefined ? (
          '—'
        ) : (
          <span className="whitespace-nowrap tabular-nums">
            {formatDateTime(locale, launch.net)}
          </span>
        ),
    },
    {
      key: 'name',
      header: t('launches.mission'),
      cell: (launch) => <span lang={launch.name_lang}>{launch.name}</span>,
    },
    {
      key: 'provider',
      header: t('common.provider'),
      cell: (launch) =>
        launch.provider === undefined ? (
          '—'
        ) : (
          <span lang={launch.provider.name_lang}>{launch.provider.name}</span>
        ),
    },
    {
      key: 'site',
      header: t('common.location'),
      cell: (launch) => launch.pad?.location ?? '—',
    },
    {
      key: 'status',
      header: t('common.status'),
      cell: (launch) => <span lang={launch.status.name_lang}>{launch.status.name}</span>,
    },
  ];

  return launches.length === 0 ? (
    <p className="text-ink-muted">{t('common.none')}</p>
  ) : (
    <DataTable caption={title} columns={columns} rows={launches} rowKey={(launch) => launch.id} />
  );
}

interface LaunchTableProps {
  readonly title: string;
  readonly query: UseQueryResult<Schemas['PageLaunchSummary']>;
}

export function LaunchTable({ title, query }: LaunchTableProps) {
  return (
    <div className="flex flex-col gap-4">
      <h3 className="font-display text-xl font-light text-ink">{title}</h3>
      <DataRegion query={query} minHeight={240}>
        {(page) => <LaunchList title={title} launches={page.items} />}
      </DataRegion>
    </div>
  );
}
