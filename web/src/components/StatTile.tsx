import type { ReactNode } from 'react';

interface StatTileProps {
  readonly label: string;
  readonly value: string;
  readonly unit?: string;
  readonly detail?: ReactNode;
  readonly note?: ReactNode;
}

export function StatTile({ label, value, unit, detail, note }: StatTileProps) {
  return (
    <div className="flex flex-col gap-2 border-t border-hairline-strong pt-4">
      <p className="hz-label">{label}</p>
      <p className="font-display text-figure leading-none font-extralight text-ink tabular-nums">
        {value}
        {unit !== undefined && (
          <span className="ml-2 text-lg font-light text-ink-muted">{unit}</span>
        )}
      </p>
      {detail !== undefined && <div className="text-sm text-ink-muted">{detail}</div>}
      {note}
    </div>
  );
}
