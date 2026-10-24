import { describe, expect, it } from 'vitest';
import en from '../src/locales/en/common.json';
import ja from '../src/locales/ja/common.json';
import { escapeHtml, PAGES, renderShell, routeHeads, type ShellCopy } from './routeShells.ts';

const SITE = 'https://example.test';
const TEMPLATE = `<!doctype html>
<html lang="en" data-theme="deep-space">
  <head>
    <title>星空 Hoshizora</title>
  </head>
  <body><div id="root"></div></body>
</html>`;

function copy(locale: 'en' | 'ja'): ShellCopy {
  return locale === 'en' ? en : ja;
}

describe('routeHeads', () => {
  it('lists home, every page and every agency profile with localized titles', () => {
    const heads = routeHeads('ja', copy('ja'), [{ key: 'jaxa', name: '宇宙航空研究開発機構' }]);

    expect(heads.map((head) => head.path)).toEqual([
      '',
      ...PAGES.map((page) => page.slug),
      'agencies/jaxa',
    ]);
    expect(heads.at(-1)?.title).toBe('宇宙航空研究開発機構｜星空');
    expect(heads.every((head) => head.description.length > 0)).toBe(true);
  });

  it('finds a title and lede for every page in both locales', () => {
    for (const locale of ['en', 'ja'] as const) {
      const { pages } = copy(locale);
      for (const { key } of PAGES) {
        expect(pages[key].title.length * pages[key].lede.length).toBeGreaterThan(0);
      }
    }
  });
});

describe('renderShell', () => {
  const [, launches] = routeHeads('ja', copy('ja'), []);

  it('names the blob after the path and groups it by depth', () => {
    const home = routeHeads('en', copy('en'), [])[0];
    if (home === undefined || launches === undefined) {
      throw new Error('missing heads');
    }

    expect([renderShell(TEMPLATE, SITE, home), renderShell(TEMPLATE, SITE, launches)]).toEqual([
      expect.objectContaining({ blob: 'en', depth: 1 }),
      expect.objectContaining({ blob: 'ja/launches', depth: 2 }),
    ]);
  });

  it('sets the language, title, canonical link and hreflang alternates', () => {
    if (launches === undefined) {
      throw new Error('missing heads');
    }
    const { html } = renderShell(TEMPLATE, SITE, launches);

    expect(html).toContain('<html lang="ja" data-theme="deep-space">');
    expect(html).toContain(`<title>${escapeHtml(launches.title)}</title>`);
    expect(html).toContain('rel="canonical" href="https://example.test/ja/launches"');
    expect(html).toContain('hreflang="en" href="https://example.test/en/launches"');
    expect(html).toContain('hreflang="x-default" href="https://example.test/launches"');
    expect(html.match(/data-route-shell/g)).toHaveLength(10);
  });

  it('escapes names that look like markup', () => {
    const profile = routeHeads('en', copy('en'), [{ key: 'x', name: 'A <b>"&"</b>' }]).find(
      (head) => head.path === 'agencies/x',
    );
    if (profile === undefined) {
      throw new Error('missing heads');
    }

    expect(renderShell(TEMPLATE, SITE, profile).html).toContain(
      '<title>A &lt;b&gt;&quot;&amp;&quot;&lt;/b&gt; · Hoshizora</title>',
    );
  });
});
