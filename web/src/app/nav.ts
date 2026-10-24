export const NAV_ITEMS = [
  { key: 'home', path: '' },
  { key: 'launches', path: 'launches' },
  { key: 'nearEarth', path: 'near-earth' },
  { key: 'sun', path: 'sun' },
  { key: 'exoplanets', path: 'exoplanets' },
  { key: 'agencies', path: 'agencies' },
  { key: 'sources', path: 'sources' },
] as const;

export type NavKey = (typeof NAV_ITEMS)[number]['key'];
