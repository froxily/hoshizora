import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { NavLink } from 'react-router';
import { NAV_ITEMS } from '../app/nav';
import type { Locale } from '../i18n/locales';
import { Brand } from './Brand';
import { DataLinkIndicator } from './DataLink';
import { LanguageToggle } from './LanguageToggle';
import { MotionToggle } from './MotionToggle';

function NavLinks({ locale, onNavigate }: { locale: Locale; onNavigate?: () => void }) {
  const { t } = useTranslation();
  return NAV_ITEMS.map((item) => (
    <li key={item.key}>
      <NavLink
        to={item.path === '' ? `/${locale}` : `/${locale}/${item.path}`}
        end={item.path === ''}
        onClick={onNavigate}
        className={({ isActive }) =>
          `relative block py-2 text-sm whitespace-nowrap transition-colors duration-[var(--hz-duration-fast)] after:absolute after:inset-x-0 after:bottom-0 after:h-px after:origin-left after:bg-amber after:transition-transform after:duration-[var(--hz-duration-reveal)] after:ease-out ${isActive ? 'text-ink after:scale-x-100' : 'text-ink-muted after:scale-x-0 hover:text-ink'}`
        }
      >
        {t(`nav.${item.key}`)}
      </NavLink>
    </li>
  ));
}

function useScrolled(threshold: number): boolean {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => {
      setScrolled(window.scrollY > threshold);
    };
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', onScroll);
    };
  }, [threshold]);
  return scrolled;
}

export function SiteHeader({ locale }: { locale: Locale }) {
  const { t } = useTranslation();
  const scrolled = useScrolled(8);
  const menu = useRef<HTMLDialogElement>(null);

  return (
    <header
      className={`fixed inset-x-0 top-0 z-30 border-b transition-colors duration-[var(--hz-duration-reveal)] ${scrolled ? 'border-hairline bg-veil-strong backdrop-blur-md' : 'border-transparent'}`}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center gap-8 px-gutter">
        <Brand locale={locale} />
        <nav aria-label={t('a11y.mainNav')} className="hidden lg:block">
          <ul className="flex items-center gap-7">
            <NavLinks locale={locale} />
          </ul>
        </nav>
        <div className="ml-auto flex items-center gap-4">
          <DataLinkIndicator />
          <div className="hidden items-center gap-3 lg:flex">
            <MotionToggle />
            <LanguageToggle current={locale} />
          </div>
          <button
            type="button"
            className="rounded-pill border border-hairline px-4 py-1.5 text-sm whitespace-nowrap text-ink-muted hover:border-amber hover:text-ink lg:hidden"
            aria-label={t('a11y.openMenu')}
            aria-haspopup="dialog"
            onClick={() => menu.current?.showModal()}
          >
            {t('menu.open')}
          </button>
        </div>
      </div>
      <dialog
        ref={menu}
        className="m-0 h-dvh max-h-none w-full max-w-none bg-canvas text-ink backdrop:bg-veil-strong open:flex open:flex-col"
      >
        <div className="flex h-16 items-center justify-between px-gutter">
          <Brand locale={locale} />
          <button
            type="button"
            className="rounded-pill border border-hairline px-4 py-1.5 text-sm text-ink-muted hover:border-amber hover:text-ink"
            aria-label={t('a11y.closeMenu')}
            onClick={() => menu.current?.close()}
          >
            {t('menu.close')}
          </button>
        </div>
        <nav aria-label={t('a11y.mainNav')} className="px-gutter pt-10">
          <ul className="flex flex-col gap-3 font-display text-2xl font-light">
            <NavLinks locale={locale} onNavigate={() => menu.current?.close()} />
          </ul>
        </nav>
        <div className="mt-auto flex flex-wrap items-center gap-3 px-gutter py-10">
          <MotionToggle />
          <LanguageToggle current={locale} />
        </div>
      </dialog>
    </header>
  );
}
