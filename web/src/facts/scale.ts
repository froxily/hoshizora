import { numberParam, textParam, yearParam, type Params } from './params';
import type { ScaleSpec } from './presentation';

export type ScaleLabelKey =
  'earth' | 'moon' | 'skytree' | 'shinkansen' | 'fuji' | 'surface' | 'center' | 'storm' | 'today';

export type Label = { readonly key: ScaleLabelKey } | { readonly text: string };

export interface Tick {
  readonly at: number;
  readonly label: Label;
}

export interface TrackModel {
  readonly kind: 'track';
  readonly fill?: readonly [number, number];
  readonly marker?: number;
  readonly ticks: readonly Tick[];
  readonly ends: readonly [Label | null, Label | null];
}

export interface BarsModel {
  readonly kind: 'bars';
  readonly bars: readonly {
    readonly label: Label;
    readonly value: number;
    readonly highlight: boolean;
  }[];
}

export type ScaleModel = TrackModel | BarsModel;

const EARTH_RADIUS_KM = 6_371;
const SKYTREE_M = 634;
const KP_MAX = 9;
const STORM_KP = 5;
const FLARE_CLASSES = ['A', 'B', 'C', 'M', 'X'] as const;

const clamp = (value: number) => Math.min(1, Math.max(0, value));
const text = (value: string | number): Label => ({ text: String(value) });

function track(model: Omit<TrackModel, 'kind'>): TrackModel {
  return { kind: 'track', ...model };
}

function flarePosition(flareClass: string): number | undefined {
  const match = /^([ABCMX])(\d+(?:\.\d+)?)$/.exec(flareClass.trim());
  if (match === null) {
    return undefined;
  }
  const index = FLARE_CLASSES.indexOf(match[1] as (typeof FLARE_CLASSES)[number]);
  const magnitude = Math.min(9.99, Math.max(1, Number(match[2])));
  return clamp((index + Math.log10(magnitude)) / FLARE_CLASSES.length);
}

export function scaleModel(
  spec: ScaleSpec,
  params: Params,
  currentYear: number,
): ScaleModel | undefined {
  switch (spec.kind) {
    case 'lunar': {
      const distance = numberParam(params, spec.param);
      if (distance === undefined) return undefined;
      const max = Math.max(1, distance) * 1.15;
      return track({
        marker: clamp(distance / max),
        ticks: [
          { at: 0, label: { key: 'earth' } },
          { at: 1 / max, label: { key: 'moon' } },
        ],
        ends: [null, null],
      });
    }
    case 'percent': {
      const share = numberParam(params, spec.param);
      if (share === undefined) return undefined;
      return track({ fill: [0, clamp(share)], ticks: [], ends: [text('0%'), text('100%')] });
    }
    case 'kp': {
      const kp = numberParam(params, spec.param);
      if (kp === undefined) return undefined;
      return track({
        fill: [0, clamp(kp / KP_MAX)],
        ticks: [{ at: STORM_KP / KP_MAX, label: { key: 'storm' } }],
        ends: [text(0), text(KP_MAX)],
      });
    }
    case 'flare': {
      const flareClass = textParam(params, spec.param);
      const position = flareClass === undefined ? undefined : flarePosition(flareClass);
      if (position === undefined) return undefined;
      return track({
        fill: [0, position],
        ticks: FLARE_CLASSES.map((letter, index) => ({
          at: index / FLARE_CLASSES.length,
          label: text(letter),
        })),
        ends: [null, null],
      });
    }
    case 'timeline': {
      const year = yearParam(params, spec.param);
      if (year === undefined) return undefined;
      const from = Math.min(spec.from, year - 5);
      const span = Math.max(1, currentYear - from);
      const at = clamp((year - from) / span);
      return track({ fill: [at, 1], marker: at, ticks: [], ends: [text(from), text(currentYear)] });
    }
    case 'span': {
      const first = yearParam(params, spec.first);
      const last = yearParam(params, spec.last);
      if (first === undefined || last === undefined || last <= first) return undefined;
      return track({
        fill: [0, 1],
        ticks: [{ at: clamp((currentYear - first) / (last - first)), label: { key: 'today' } }],
        ends: [text(first), text(last)],
      });
    }
    case 'skytree': {
      const min = numberParam(params, spec.min);
      const max = numberParam(params, spec.max);
      if (min === undefined || max === undefined) return undefined;
      const axis = Math.max(max, SKYTREE_M) * 1.1;
      return track({
        fill: [clamp(min / axis), clamp(max / axis)],
        ticks: [{ at: SKYTREE_M / axis, label: { key: 'skytree' } }],
        ends: [text('0 m'), null],
      });
    }
    case 'multiple': {
      const times = numberParam(params, spec.param);
      if (times === undefined || times < 1) return undefined;
      const decades = Math.max(1, Math.ceil(Math.log10(times)));
      return track({
        fill: [0, clamp(Math.log10(times) / decades)],
        marker: clamp(Math.log10(times) / decades),
        ticks: Array.from({ length: decades + 1 }, (_, power) => ({
          at: power / decades,
          label: power === 0 ? { key: spec.reference } : text(`×${String(10 ** power)}`),
        })),
        ends: [null, null],
      });
    }
    case 'earthDistance': {
      const distance = numberParam(params, spec.param);
      if (distance === undefined) return undefined;
      const axis = Math.max(distance, EARTH_RADIUS_KM * 2) * 1.2;
      return track({
        fill: [0, EARTH_RADIUS_KM / axis],
        marker: clamp(distance / axis),
        ticks: [{ at: EARTH_RADIUS_KM / axis, label: { key: 'surface' } }],
        ends: [{ key: 'center' }, null],
      });
    }
    case 'ratio': {
      const ratio = numberParam(params, spec.param);
      const year = yearParam(params, spec.year);
      if (ratio === undefined || year === undefined || ratio <= 0) return undefined;
      const max = Math.max(1, ratio);
      return {
        kind: 'bars',
        bars: [
          { label: text(year - 1), value: 1 / max, highlight: false },
          { label: text(year), value: ratio / max, highlight: true },
        ],
      };
    }
  }
}
