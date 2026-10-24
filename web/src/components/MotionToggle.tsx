import { useTranslation } from 'react-i18next';
import { chooseMotion, useMotion } from '../motion/motion';

export function MotionToggle() {
  const { t } = useTranslation();
  const reduced = useMotion() === 'reduced';

  return (
    <button
      type="button"
      aria-pressed={reduced}
      onClick={() => {
        chooseMotion(reduced ? 'full' : 'reduced');
      }}
      className="flex items-center gap-2 rounded-pill whitespace-nowrap border border-hairline px-3 py-1.5 text-sm text-ink-muted transition-colors duration-[var(--hz-duration-fast)] hover:border-amber hover:text-ink"
    >
      <span
        className={`relative h-3 w-6 rounded-pill border transition-colors duration-[var(--hz-duration-fast)] ${reduced ? 'border-amber bg-amber-soft' : 'border-hairline-strong'}`}
        aria-hidden
      >
        <span
          className={`absolute top-1/2 size-1.5 -translate-y-1/2 rounded-full transition-[left] duration-[var(--hz-duration-fast)] ${reduced ? 'left-3.5 bg-amber' : 'left-0.5 bg-ink-faint'}`}
        />
      </span>
      {t('motion.reduce')}
    </button>
  );
}
