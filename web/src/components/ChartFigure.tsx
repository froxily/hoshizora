import { useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { LazyChart } from '../charts/LazyChart';
import type { ChartOption } from '../charts/echarts';
import { DataTable, type Column } from './DataTable';
import { SourceNote } from './SourceNote';

interface ChartFigureProps<Row> {
  readonly title: string;
  readonly description: string;
  readonly option: ChartOption;
  readonly height?: number;
  readonly columns: readonly Column<Row>[];
  readonly rows: readonly Row[];
  readonly rowKey: (row: Row) => string;
  readonly sources: readonly string[];
  readonly asOf?: string;
  readonly aside?: ReactNode;
  readonly visibleTitle?: boolean;
  readonly legend?: readonly { readonly label: string; readonly color: string }[];
}

export function ChartFigure<Row>({
  title,
  description,
  option,
  height = 320,
  columns,
  rows,
  rowKey,
  sources,
  asOf,
  aside,
  visibleTitle = false,
  legend,
}: ChartFigureProps<Row>) {
  const { t } = useTranslation();
  const [view, setView] = useState<'chart' | 'table'>('chart');

  return (
    <figure className="flex flex-col gap-4">
      <figcaption className="flex flex-wrap items-start justify-between gap-x-6 gap-y-3">
        <span className="max-w-2xl">
          <span
            className={visibleTitle ? 'block font-display text-xl font-light text-ink' : 'sr-only'}
          >
            {title}
          </span>
          <span className={`block text-sm text-ink-muted ${visibleTitle ? 'mt-1' : ''}`}>
            {description}
          </span>
        </span>
        <span
          role="group"
          aria-label={t('chart.viewAs')}
          className="flex rounded-pill border border-hairline p-0.5"
        >
          {(['chart', 'table'] as const).map((option) => (
            <button
              key={option}
              type="button"
              aria-pressed={view === option}
              onClick={() => {
                setView(option);
              }}
              className={`rounded-pill px-3 py-1 text-xs transition-colors duration-[var(--hz-duration-fast)] ${view === option ? 'bg-surface-raised text-ink' : 'text-ink-muted hover:text-ink'}`}
            >
              {t(`chart.${option}`)}
            </button>
          ))}
        </span>
      </figcaption>
      {view === 'chart' && legend !== undefined && legend.length > 0 && (
        <ul className="flex flex-wrap gap-x-5 gap-y-2" aria-hidden>
          {legend.map((entry) => (
            <li key={entry.label} className="flex items-center gap-2 text-xs text-ink-muted">
              <span className="size-2.5 rounded-sm" style={{ backgroundColor: entry.color }} />
              {entry.label}
            </li>
          ))}
        </ul>
      )}
      {view === 'chart' ? (
        <LazyChart option={option} height={height} label={`${title}. ${description}`} />
      ) : (
        <DataTable caption={title} columns={columns} rows={rows} rowKey={rowKey} />
      )}
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <SourceNote sources={sources} {...(asOf === undefined ? {} : { asOf })} />
        {aside}
      </div>
    </figure>
  );
}
