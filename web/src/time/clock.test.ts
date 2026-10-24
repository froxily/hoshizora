import { describe, expect, it } from 'vitest';
import { JST_OFFSET_MS, readout } from './clock';

describe('mission clock readout', () => {
  const instant = Date.UTC(2026, 9, 18, 15, 4, 31);

  it('reads UTC', () => {
    expect(readout(instant)).toEqual({ date: '2026-10-18', time: '15:04:31' });
  });

  it('reads JST nine hours ahead, across midnight', () => {
    expect(readout(instant, JST_OFFSET_MS)).toEqual({ date: '2026-10-19', time: '00:04:31' });
  });
});
