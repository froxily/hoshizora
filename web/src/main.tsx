import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter } from 'react-router';
import { RouterProvider } from 'react-router/dom';
import { routes } from './app/routes';
import { initI18n } from './i18n/i18n';
import { localeFromPath } from './i18n/locales';
import { preferredLocale } from './i18n/preference';
import { applyMotion } from './motion/motion';
import './styles/index.css';

const container = document.getElementById('root');
if (container === null) {
  throw new Error('Missing #root element');
}

for (const prerendered of document.querySelectorAll('[data-route-shell]')) {
  prerendered.remove();
}

initI18n(localeFromPath(window.location.pathname) ?? preferredLocale());
applyMotion();

createRoot(container).render(
  <StrictMode>
    <RouterProvider router={createBrowserRouter(routes)} />
  </StrictMode>,
);
