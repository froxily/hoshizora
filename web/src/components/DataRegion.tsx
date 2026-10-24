import type { UseQueryResult } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { DataErrorPanel, DataLinkPanel } from './DataLink';

interface DataRegionProps<T> {
  readonly query: UseQueryResult<T>;
  readonly compact?: boolean;
  readonly minHeight?: number;
  readonly placeholderClassName?: string;
  readonly children: (data: T) => ReactNode;
}

export function DataRegion<T>({
  query,
  compact = false,
  minHeight,
  placeholderClassName = '',
  children,
}: DataRegionProps<T>) {
  if (query.isSuccess) {
    return children(query.data);
  }
  return (
    <div
      style={minHeight === undefined ? undefined : { minHeight }}
      className={`flex flex-col ${placeholderClassName}`}
    >
      {query.isError ? (
        <DataErrorPanel
          onRetry={() => {
            void query.refetch();
          }}
        />
      ) : (
        <DataLinkPanel compact={compact} />
      )}
    </div>
  );
}
