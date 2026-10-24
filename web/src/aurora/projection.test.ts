import { describe, expect, it } from 'vitest';
import { chanceAt, project } from './projection';

describe('aurora polar projection', () => {
  it('puts the pole at the center and the 40° edge on the rim', () => {
    expect(project(0, 90, 'north', 100)).toEqual({ x: 0, y: 0 });
    const edge = project(90, 40, 'north', 100);
    expect(edge?.x).toBeCloseTo(100);
    expect(edge?.y).toBeCloseTo(0);
  });

  it('draws Greenwich downward in the north and upward in the south', () => {
    expect(project(0, 65, 'north', 100)?.y).toBeGreaterThan(0);
    expect(project(0, -65, 'south', 100)?.y).toBeLessThan(0);
  });

  it('leaves out latitudes beyond the map edge and the other hemisphere', () => {
    expect(project(140, 35, 'north', 100)).toBeNull();
    expect(project(140, 60, 'south', 100)).toBeNull();
  });

  it('reads the chance at the nearest cell, wrapping west longitudes', () => {
    const cells = [
      [212, 65, 18],
      [19, 70, 7],
    ];
    expect(chanceAt(cells, -147.72, 64.84)).toBe(18);
    expect(chanceAt(cells, 18.96, 69.65)).toBe(7);
    expect(chanceAt(cells, 139.69, 35.68)).toBe(0);
  });
});
