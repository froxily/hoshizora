export const SHELL_LOCALES = ['en', 'ja'] as const;

export type ShellLocale = (typeof SHELL_LOCALES)[number];

export const PAGES = [
  { slug: 'launches', key: 'launches' },
  { slug: 'near-earth', key: 'nearEarth' },
  { slug: 'sun', key: 'sun' },
  { slug: 'exoplanets', key: 'exoplanets' },
  { slug: 'agencies', key: 'agencies' },
  { slug: 'sources', key: 'sources' },
] as const;

export type PageKey = (typeof PAGES)[number]['key'];

export interface ShellCopy {
  meta: { title: string; pageTitle: string; description: string };
  pages: Record<PageKey, { title: string; lede: string }>;
}

export interface Agency {
  key: string;
  name: string;
}

export interface RouteHead {
  locale: ShellLocale;
  path: string;
  title: string;
  description: string;
}

export interface Shell {
  blob: string;
  depth: number;
  html: string;
}

const OG_LOCALE: Record<ShellLocale, string> = { en: 'en_US', ja: 'ja_JP' };
const SHELL_MARK = 'data-route-shell';

function pageTitle(copy: ShellCopy, page: string): string {
  return copy.meta.pageTitle.replace('{{page}}', page);
}

export function routeHeads(
  locale: ShellLocale,
  copy: ShellCopy,
  agencies: readonly Agency[],
): RouteHead[] {
  const home = { locale, path: '', title: copy.meta.title, description: copy.meta.description };
  const pages = PAGES.map(({ slug, key }) => ({
    locale,
    path: slug,
    title: pageTitle(copy, copy.pages[key].title),
    description: copy.pages[key].lede,
  }));
  const profiles = agencies.map((agency) => ({
    locale,
    path: `agencies/${agency.key}`,
    title: pageTitle(copy, agency.name),
    description: copy.meta.description,
  }));
  return [home, ...pages, ...profiles];
}

export function escapeHtml(text: string): string {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function localizedUrl(site: string, locale: ShellLocale, path: string): string {
  return `${site}/${locale}${path === '' ? '' : `/${path}`}`;
}

function headTags(site: string, head: RouteHead): string {
  const canonical = localizedUrl(site, head.locale, head.path);
  const alternates = SHELL_LOCALES.map(
    (locale) =>
      `<link ${SHELL_MARK} rel="alternate" hreflang="${locale}" href="${localizedUrl(site, locale, head.path)}" />`,
  );
  const tags = [
    `<meta ${SHELL_MARK} name="description" content="${escapeHtml(head.description)}" />`,
    `<link ${SHELL_MARK} rel="canonical" href="${canonical}" />`,
    ...alternates,
    `<link ${SHELL_MARK} rel="alternate" hreflang="x-default" href="${site}/${head.path}" />`,
    `<meta ${SHELL_MARK} property="og:type" content="website" />`,
    `<meta ${SHELL_MARK} property="og:url" content="${canonical}" />`,
    `<meta ${SHELL_MARK} property="og:title" content="${escapeHtml(head.title)}" />`,
    `<meta ${SHELL_MARK} property="og:description" content="${escapeHtml(head.description)}" />`,
    `<meta ${SHELL_MARK} property="og:locale" content="${OG_LOCALE[head.locale]}" />`,
  ];
  return tags.map((tag) => `    ${tag}\n`).join('');
}

export function renderShell(template: string, site: string, head: RouteHead): Shell {
  const html = template
    .replace(/<html lang="[^"]*"/, `<html lang="${head.locale}"`)
    .replace(/<title>[^<]*<\/title>/, `<title>${escapeHtml(head.title)}</title>`)
    .replace('</head>', `${headTags(site, head)}  </head>`);
  const blob = head.path === '' ? head.locale : `${head.locale}/${head.path}`;
  return { blob, depth: blob.split('/').length, html };
}
