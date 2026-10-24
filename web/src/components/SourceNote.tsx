import { useQuery } from '@tanstack/react-query';
import { useId } from 'react';
import { useTranslation } from 'react-i18next';
import { sourcesQuery } from '../api/queries';
import { formatDateTime } from '../format/format';
import { useLocale } from '../i18n/useLocale';

interface SourceNoteProps {
  readonly sources: readonly string[];
  readonly asOf?: string;
}

function useLastSuccess(slug: string | undefined, skip: boolean): string | undefined {
  const locale = useLocale();
  const query = useQuery({ ...sourcesQuery(locale), enabled: !skip && slug !== undefined });
  const source = query.data?.items.find((item) => item.slug === slug);
  return source?.status.last_succeeded_at ?? source?.status.last_fetched_at;
}

export function SourceNote({ sources, asOf }: SourceNoteProps) {
  const { t } = useTranslation();
  const locale = useLocale();
  const panelId = useId();
  const fetched = useLastSuccess(sources[0], asOf !== undefined);
  const shown = asOf ?? fetched;

  return (
    <span className="group relative inline-flex">
      <button
        type="button"
        aria-describedby={panelId}
        aria-label={t('source.show')}
        className="text-xs text-ink-muted underline decoration-ink-faint decoration-dotted underline-offset-4 transition-colors duration-[var(--hz-duration-fast)] hover:text-ink"
        onKeyDown={(event) => {
          if (event.key === 'Escape') {
            event.currentTarget.blur();
          }
        }}
      >
        {t('source.label')}
      </button>
      <span
        id={panelId}
        role="tooltip"
        className="invisible absolute bottom-full left-0 z-20 mb-2 w-64 rounded border border-hairline-strong bg-surface-raised px-4 py-3 text-xs leading-relaxed text-ink-muted opacity-0 shadow-lg transition-opacity duration-[var(--hz-duration-fast)] group-focus-within:visible group-focus-within:opacity-100 group-hover:visible group-hover:opacity-100"
      >
        <span className="block text-ink">
          {sources
            .map((source) => t(`source.names.${source}`, { defaultValue: source }))
            .join(' · ')}
        </span>
        {shown !== undefined && (
          <span className="mt-1 block">
            {t('source.asOf')}: {formatDateTime(locale, shown)}
          </span>
        )}
      </span>
    </span>
  );
}
