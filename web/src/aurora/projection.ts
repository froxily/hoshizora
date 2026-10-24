export type Hemisphere = 'north' | 'south';

export const EDGE_LATITUDE = 40;

export interface Point {
  readonly x: number;
  readonly y: number;
}

export function project(
  longitude: number,
  latitude: number,
  hemisphere: Hemisphere,
  radius: number,
): Point | null {
  const polar = hemisphere === 'north' ? latitude : -latitude;
  if (polar < EDGE_LATITUDE) {
    return null;
  }
  const distance = ((90 - polar) / (90 - EDGE_LATITUDE)) * radius;
  const angle = (longitude * Math.PI) / 180;
  const vertical = hemisphere === 'north' ? Math.cos(angle) : -Math.cos(angle);
  return { x: distance * Math.sin(angle), y: distance * vertical };
}

export function chanceAt(
  cells: readonly (readonly number[])[],
  longitude: number,
  latitude: number,
): number {
  const lon = ((Math.round(longitude) % 360) + 360) % 360;
  const lat = Math.round(latitude);
  const cell = cells.find((candidate) => candidate[0] === lon && candidate[1] === lat);
  return cell?.[2] ?? 0;
}

export interface Place {
  readonly key:
    'tromso' | 'fairbanks' | 'yellowknife' | 'rikubetsu' | 'tokyo' | 'hobart' | 'ushuaia';
  readonly longitude: number;
  readonly latitude: number;
}

export const PLACES: readonly Place[] = [
  { key: 'tromso', longitude: 18.96, latitude: 69.65 },
  { key: 'fairbanks', longitude: -147.72, latitude: 64.84 },
  { key: 'yellowknife', longitude: -114.37, latitude: 62.45 },
  { key: 'rikubetsu', longitude: 143.74, latitude: 43.47 },
  { key: 'tokyo', longitude: 139.69, latitude: 35.68 },
  { key: 'hobart', longitude: 147.33, latitude: -42.88 },
  { key: 'ushuaia', longitude: -68.3, latitude: -54.8 },
];
