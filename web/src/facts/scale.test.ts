import { describe, expect, it } from 'vitest';
import { scaleModel, type TrackModel } from './scale';

const YEAR = 2026;

function track(model: ReturnType<typeof scaleModel>): TrackModel {
  if (model?.kind !== 'track') {
    throw new Error('expected a track');
  }
  return model;
}

describe('fact scales', () => {
  it('puts a flyby inside the Moon distance between Earth and the Moon', () => {
    const model = track(scaleModel({ kind: 'lunar', param: 'distance' }, { distance: 0.3 }, YEAR));
    const moon = model.ticks[1]?.at ?? 0;
    expect(model.marker).toBeGreaterThan(0);
    expect(model.marker).toBeLessThan(moon);
  });

  it('puts a distant flyby beyond the Moon', () => {
    const model = track(scaleModel({ kind: 'lunar', param: 'distance' }, { distance: 4.7 }, YEAR));
    expect(model.marker).toBeGreaterThan(model.ticks[1]?.at ?? 1);
  });

  it('places flare classes on a logarithmic A to X scale', () => {
    const m23 = track(scaleModel({ kind: 'flare', param: 'c' }, { c: 'M2.3' }, YEAR));
    const x1 = track(scaleModel({ kind: 'flare', param: 'c' }, { c: 'X1.0' }, YEAR));
    expect(m23.fill?.[1]).toBeCloseTo((3 + Math.log10(2.3)) / 5);
    expect(x1.fill?.[1]).toBeCloseTo(0.8);
  });

  it('marks the storm threshold on the Kp scale', () => {
    const model = track(scaleModel({ kind: 'kp', param: 'kp' }, { kp: 6.33 }, YEAR));
    expect(model.ticks[0]?.at).toBeCloseTo(5 / 9);
    expect(model.fill?.[1]).toBeCloseTo(6.33 / 9);
  });

  it('compares a size range with Tokyo Skytree', () => {
    const model = track(
      scaleModel({ kind: 'skytree', min: 'a', max: 'b' }, { a: 2800, b: 6300 }, YEAR),
    );
    expect(model.ticks[0]?.at).toBeCloseTo(634 / (6300 * 1.1));
    expect(model.fill?.[1]).toBeCloseTo(1 / 1.1);
  });

  it('draws a speed multiple on a log scale from the reference', () => {
    const model = track(
      scaleModel({ kind: 'multiple', param: 't', reference: 'shinkansen' }, { t: 296 }, YEAR),
    );
    expect(model.ticks.map((tick) => tick.label)).toEqual([
      { key: 'shinkansen' },
      { text: '×10' },
      { text: '×100' },
      { text: '×1000' },
    ]);
    expect(model.marker).toBeCloseTo(Math.log10(296) / 3);
  });

  it('compares this year with last year', () => {
    expect(
      scaleModel({ kind: 'ratio', param: 'r', year: 'y' }, { r: 1.25, y: '2026' }, YEAR),
    ).toEqual({
      kind: 'bars',
      bars: [
        { label: { text: '2025' }, value: 0.8, highlight: false },
        { label: { text: '2026' }, value: 1, highlight: true },
      ],
    });
  });

  it('draws nothing for unusable parameters', () => {
    expect(scaleModel({ kind: 'flare', param: 'c' }, { c: 'none' }, YEAR)).toBeUndefined();
    expect(scaleModel({ kind: 'percent', param: 's' }, {}, YEAR)).toBeUndefined();
  });
});
