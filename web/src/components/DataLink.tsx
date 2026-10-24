import { useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useDataLink, type DataLinkState } from '../api/dataLink';
import { retryStalledQueries } from '../api/queryClient';
import { useNow } from '../time/now';

function elapsedClock(since: number, now: number): string {
  const seconds = Math.max(0, Math.floor((now - since) / 1_000));
  return `${String(Math.floor(seconds / 60))}:${String(seconds % 60).padStart(2, '0')}`;
}

function Elapsed({ since }: { since: number }) {
  const { t } = useTranslation();
  const now = useNow();
  return (
    <span className="tabular-nums">
      {t('dataLink.elapsed', { time: elapsedClock(since, now) })}
    </span>
  );
}

const DOT: Record<DataLinkState['status'], string> = {
  idle: 'bg-ink-faint',
  connected: 'bg-positive',
  waking: 'bg-cyan animate-[hz-pulse_1.8s_ease-in-out_infinite] motion-reduced:animate-none',
  offline: 'bg-amber',
};

const LABEL = {
  idle: 'dataLink.connecting',
  connected: 'dataLink.live',
  waking: 'dataLink.waking',
  offline: 'dataLink.offline',
} as const;

export function DataLinkIndicator() {
  const { t } = useTranslation();
  const link = useDataLink();
  return (
    <p className="flex items-center gap-2 text-xs text-ink-muted" role="status" aria-live="polite">
      <span className={`size-1.5 shrink-0 rounded-full ${DOT[link.status]}`} aria-hidden />
      <span className="sr-only sm:not-sr-only">{t(LABEL[link.status])}</span>
    </p>
  );
}

export function ScanLine() {
  return (
    <span className="pointer-events-none absolute inset-x-0 top-0 h-px overflow-hidden" aria-hidden>
      <span className="block h-full w-1/3 bg-linear-to-r from-transparent via-cyan to-transparent animate-[hz-scan_2.4s_linear_infinite] motion-reduced:w-full motion-reduced:animate-none motion-reduced:opacity-30" />
    </span>
  );
}

export function DataLinkPanel({ compact = false }: { compact?: boolean }) {
  const { t } = useTranslation();
  const link = useDataLink();
  const client = useQueryClient();
  const offline = link.status === 'offline';
  const waking = link.status === 'waking' || offline;

  return (
    <div
      className="relative flex h-full min-h-24 flex-col justify-center gap-2 overflow-hidden rounded border border-hairline bg-cyan-soft/40 px-5 py-4"
      role="status"
      aria-live="polite"
    >
      <ScanLine />
      <p className={`text-sm ${offline ? 'text-amber' : 'text-cyan'}`}>
        {t(offline ? 'dataLink.offline' : waking ? 'dataLink.waking' : 'dataLink.waiting')}
      </p>
      {waking && !compact && (
        <p className="max-w-prose text-sm text-ink-muted">
          {t(offline ? 'dataLink.offlineDetail' : 'dataLink.wakingDetail')}
        </p>
      )}
      {waking && link.since !== null && (
        <p className="text-xs text-ink-muted">
          <Elapsed since={link.since} />
        </p>
      )}
      {offline && (
        <button
          type="button"
          onClick={() => void retryStalledQueries(client)}
          className="self-start rounded-pill border border-hairline-strong px-4 py-1.5 text-sm text-ink transition-colors duration-[var(--hz-duration-fast)] hover:border-amber"
        >
          {t('dataLink.retry')}
        </button>
      )}
    </div>
  );
}

export function DataErrorPanel({ onRetry }: { onRetry: () => void }) {
  const { t } = useTranslation();
  return (
    <div
      className="flex h-full min-h-24 flex-col justify-center gap-2 rounded border border-hairline px-5 py-4"
      role="alert"
    >
      <p className="text-sm text-amber">{t('dataLink.failed')}</p>
      <p className="max-w-prose text-sm text-ink-muted">{t('dataLink.failedDetail')}</p>
      <button
        type="button"
        onClick={onRetry}
        className="self-start rounded-pill border border-hairline-strong px-4 py-1.5 text-sm text-ink transition-colors duration-[var(--hz-duration-fast)] hover:border-amber"
      >
        {t('dataLink.retry')}
      </button>
    </div>
  );
}
