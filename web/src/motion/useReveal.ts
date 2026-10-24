import { useEffect, useRef, useState, type RefObject } from 'react';

export type Reveal = 'initial' | 'hidden' | 'revealed';

export const REVEAL_CLASS: Record<Reveal, string> = {
  initial: 'hz-rise',
  hidden: 'opacity-0',
  revealed: 'hz-reveal',
};

export function useReveal<T extends Element>(): [RefObject<T | null>, Reveal] {
  const target = useRef<T>(null);
  const [reveal, setReveal] = useState<Reveal>('initial');

  useEffect(() => {
    const element = target.current;
    if (element === null || typeof IntersectionObserver !== 'function') {
      return;
    }
    let first = true;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries.some((entry) => entry.isIntersecting);
        if (first) {
          first = false;
          if (visible) {
            observer.disconnect();
          } else {
            setReveal('hidden');
          }
          return;
        }
        if (visible) {
          setReveal('revealed');
          observer.disconnect();
        }
      },
      { rootMargin: '100000px 0px -10% 0px' },
    );
    observer.observe(element);
    return () => {
      observer.disconnect();
    };
  }, []);

  return [target, reveal];
}
