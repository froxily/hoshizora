export const JST_OFFSET_MS = 9 * 3_600_000;

export interface Readout {
  readonly date: string;
  readonly time: string;
}

export function readout(instant: number, offsetMs = 0): Readout {
  const iso = new Date(instant + offsetMs).toISOString();
  return { date: iso.slice(0, 10), time: iso.slice(11, 19) };
}
