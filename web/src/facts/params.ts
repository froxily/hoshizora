export type Params = Readonly<Record<string, unknown>>;

export function numberParam(params: Params, key: string): number | undefined {
  const value = params[key];
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim() !== '' && Number.isFinite(Number(value))) {
    return Number(value);
  }
  return undefined;
}

export function yearParam(params: Params, key: string): number | undefined {
  const value = params[key];
  if (typeof value === 'string') {
    const year = Number(value.slice(0, 4));
    return Number.isInteger(year) && year > 0 ? year : undefined;
  }
  return typeof value === 'number' && Number.isInteger(value) ? value : undefined;
}

export function textParam(params: Params, key: string): string | undefined {
  const value = params[key];
  return typeof value === 'string' && value !== '' ? value : undefined;
}
