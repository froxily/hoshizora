import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { createMemoryRouter } from 'react-router';
import { RouterProvider } from 'react-router/dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { LOCALE_STORAGE_KEY } from '../i18n/preference';
import en from '../locales/en/common.json';
import ja from '../locales/ja/common.json';
import { routes } from './routes';

function browserLanguages(...languages: string[]) {
  vi.spyOn(window.navigator, 'languages', 'get').mockReturnValue(languages);
}

function renderAt(path: string) {
  const router = createMemoryRouter(routes, { initialEntries: [path] });
  render(<RouterProvider router={router} />);
  return router;
}

describe('locale routing', () => {
  beforeEach(() => {
    browserLanguages('en-US');
  });

  it('sends the root to the browser language', async () => {
    browserLanguages('ja-JP', 'en-US');

    const router = renderAt('/');

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/ja');
    });
  });

  it('prefers the saved language over the browser language', async () => {
    browserLanguages('ja-JP');
    window.localStorage.setItem(LOCALE_STORAGE_KEY, 'en');

    const router = renderAt('/');

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/en');
    });
  });

  it('adds the locale prefix to unprefixed paths and keeps the query', async () => {
    const router = renderAt('/launches?year=2026');

    await waitFor(() => {
      expect(router.state.location.pathname).toBe('/en/launches');
    });
    expect(router.state.location.search).toBe('?year=2026');
  });

  it('renders Japanese with matching document language and title', async () => {
    renderAt('/ja');

    expect(await screen.findByRole('heading', { level: 1, name: ja.home.title })).toBeDefined();
    expect(document.documentElement.lang).toBe('ja');
    expect(document.title).toBe(ja.meta.title);
  });

  it('advertises every language version through hreflang', async () => {
    renderAt('/en/launches');
    await screen.findByRole(
      'heading',
      { level: 1, name: en.pages.launches.title },
      { timeout: 5_000 },
    );

    const alternates = [...document.head.querySelectorAll('link[rel="alternate"]')].map((link) => [
      link.getAttribute('hreflang'),
      new URL(link.getAttribute('href') ?? '').pathname,
    ]);

    expect(alternates).toEqual([
      ['en', '/en/launches'],
      ['ja', '/ja/launches'],
      ['x-default', '/launches'],
    ]);
  });

  it('switches language from the toggle and remembers the choice', async () => {
    const router = renderAt('/en');
    const toggle = await screen.findByRole('link', {
      name: en.language.switchTo.replace('{{language}}', en.language.name.ja),
    });

    act(() => {
      fireEvent.click(toggle);
    });

    expect(await screen.findByRole('heading', { level: 1, name: ja.home.title })).toBeDefined();
    expect(router.state.location.pathname).toBe('/ja');
    expect(window.localStorage.getItem(LOCALE_STORAGE_KEY)).toBe('ja');
    expect(document.documentElement.lang).toBe('ja');
  });
});
