import { useTranslation } from 'react-i18next';
import type { BarsModel, Label, ScaleModel, TrackModel } from './scale';

const EDGE = 0.1;

function useLabel(): (label: Label) => string {
  const { t } = useTranslation();
  return (label) => ('key' in label ? t(`scale.${label.key}`) : label.text);
}

function percent(value: number): string {
  return `${String(value * 100)}%`;
}

function tickAlignment(at: number): string {
  if (at < EDGE) return 'translate-x-0 text-left';
  if (at > 1 - EDGE) return '-translate-x-full text-right';
  return '-translate-x-1/2 text-center';
}

function Track({ model }: { model: TrackModel }) {
  const label = useLabel();
  const [start, end] = model.ends;
  return (
    <div>
      <div className="relative h-5">
        <span className="absolute inset-x-0 top-2 h-px bg-hairline-strong" />
        {model.fill !== undefined && (
          <span
            className="absolute top-[7px] h-[3px] rounded-full bg-[var(--fact-accent)]"
            style={{
              left: percent(model.fill[0]),
              width: percent(Math.max(0.004, model.fill[1] - model.fill[0])),
            }}
          />
        )}
        {model.ticks.map((tick) => (
          <span
            key={`${String(tick.at)}-${label(tick.label)}`}
            className="absolute top-0.5 h-3.5 w-px bg-ink-muted"
            style={{ left: percent(tick.at) }}
          />
        ))}
        {model.marker !== undefined && (
          <span
            className="absolute top-[3px] size-2.5 -translate-x-1/2 rounded-full bg-[var(--fact-accent)] ring-2 ring-canvas"
            style={{ left: percent(model.marker) }}
          />
        )}
      </div>
      {model.ticks.length > 0 && (
        <div className="relative h-5">
          {model.ticks.map((tick) => (
            <span
              key={`${String(tick.at)}-${label(tick.label)}`}
              className={`absolute top-0 text-xs whitespace-nowrap text-ink-muted ${tickAlignment(tick.at)}`}
              style={{ left: percent(tick.at) }}
            >
              {label(tick.label)}
            </span>
          ))}
        </div>
      )}
      {(start !== null || end !== null) && (
        <div className="flex justify-between text-xs text-ink-muted tabular-nums">
          <span>{start === null ? '' : label(start)}</span>
          <span>{end === null ? '' : label(end)}</span>
        </div>
      )}
    </div>
  );
}

function Bars({ model }: { model: BarsModel }) {
  const label = useLabel();
  return (
    <div className="space-y-1.5">
      {model.bars.map((bar) => (
        <div key={label(bar.label)} className="flex items-center gap-3">
          <span className="w-10 text-xs text-ink-muted tabular-nums">{label(bar.label)}</span>
          <span className="relative h-[3px] flex-1">
            <span
              className={`absolute inset-y-0 left-0 rounded-full ${bar.highlight ? 'bg-[var(--fact-accent)]' : 'bg-ink-muted'}`}
              style={{ width: percent(bar.value) }}
            />
          </span>
        </div>
      ))}
    </div>
  );
}

export function ScaleBar({ model }: { model: ScaleModel }) {
  return (
    <div aria-hidden className="pt-1">
      {model.kind === 'track' ? <Track model={model} /> : <Bars model={model} />}
    </div>
  );
}
