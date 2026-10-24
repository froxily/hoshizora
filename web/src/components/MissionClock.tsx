import { useTranslation } from 'react-i18next';
import { JST_OFFSET_MS, readout, type Readout } from '../time/clock';
import { useNow } from '../time/now';

function Zone({ label, value, zone }: { label: string; value: Readout; zone: string }) {
  return (
    <p className="flex items-baseline gap-3 whitespace-nowrap">
      <span className="hz-label text-ink-muted">{label}</span>
      <time dateTime={`${value.date}T${value.time}${zone}`} className="flex items-baseline gap-2">
        <span className="text-sm text-ink-muted tabular-nums">{value.date}</span>
        <span className="font-display text-xl font-light text-ink tabular-nums">{value.time}</span>
      </time>
    </p>
  );
}

export function MissionClock() {
  const { t } = useTranslation();
  const now = useNow();

  return (
    <div
      role="group"
      aria-label={t('clock.label')}
      className="flex w-fit flex-wrap items-center gap-x-8 gap-y-3 rounded border border-hairline bg-veil px-5 py-3 backdrop-blur-sm"
    >
      <span className="size-1.5 rounded-full bg-amber" aria-hidden />
      <Zone label={t('clock.utc')} value={readout(now)} zone="Z" />
      <Zone label={t('clock.jst')} value={readout(now, JST_OFFSET_MS)} zone="+09:00" />
    </div>
  );
}
