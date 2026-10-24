import { lazy, Suspense, useEffect, useRef, useState, type RefObject } from 'react';
import { useReducedMotion } from '../motion/motion';
import { HeroPoster } from './HeroPoster';
import { chooseQuality, deviceHints, supportsWebGl, type HeroQuality } from './quality';

const HeroScene = lazy(() => import('./HeroScene'));

const IDLE_TIMEOUT_MS = 3_000;

function afterLoadAndIdle(callback: () => void): () => void {
  let idleHandle: number | null = null;
  const schedule = () => {
    idleHandle =
      typeof window.requestIdleCallback === 'function'
        ? window.requestIdleCallback(callback, { timeout: IDLE_TIMEOUT_MS })
        : window.setTimeout(callback, IDLE_TIMEOUT_MS / 2);
  };
  if (document.readyState === 'complete') {
    schedule();
  } else {
    window.addEventListener('load', schedule, { once: true });
  }
  return () => {
    window.removeEventListener('load', schedule);
    if (idleHandle !== null) {
      if (typeof window.cancelIdleCallback === 'function') {
        window.cancelIdleCallback(idleHandle);
      } else {
        window.clearTimeout(idleHandle);
      }
    }
  };
}

function useOnScreen(target: RefObject<Element | null>): boolean {
  const [inView, setInView] = useState(true);
  const [pageVisible, setPageVisible] = useState(() => document.visibilityState === 'visible');

  useEffect(() => {
    const element = target.current;
    if (element === null || typeof IntersectionObserver !== 'function') {
      return;
    }
    const observer = new IntersectionObserver(([entry]) => {
      setInView(entry?.isIntersecting ?? true);
    });
    observer.observe(element);
    return () => {
      observer.disconnect();
    };
  }, [target]);

  useEffect(() => {
    const onChange = () => {
      setPageVisible(document.visibilityState === 'visible');
    };
    document.addEventListener('visibilitychange', onChange);
    return () => {
      document.removeEventListener('visibilitychange', onChange);
    };
  }, []);

  return inView && pageVisible;
}

export function HeroBackdrop() {
  const reduced = useReducedMotion();
  const container = useRef<HTMLDivElement>(null);
  const onScreen = useOnScreen(container);
  const [quality, setQuality] = useState<HeroQuality | null>(null);
  const [sceneReady, setSceneReady] = useState(false);

  useEffect(() => {
    if (!supportsWebGl()) {
      return;
    }
    return afterLoadAndIdle(() => {
      setQuality(chooseQuality(deviceHints()));
    });
  }, []);

  return (
    <div
      ref={container}
      className="absolute inset-x-0 top-0 h-svh min-h-[34rem] overflow-hidden"
      aria-hidden
    >
      <HeroPoster />
      {quality !== null && (
        <Suspense fallback={null}>
          <div
            className={`absolute inset-0 transition-opacity duration-[var(--hz-duration-slow)] ease-out ${sceneReady ? 'opacity-100' : 'opacity-0'}`}
          >
            <HeroScene
              animate={!reduced && onScreen}
              quality={quality}
              onReady={() => {
                setSceneReady(true);
              }}
            />
          </div>
        </Suspense>
      )}
      <div className="absolute inset-x-0 bottom-0 h-1/6 bg-linear-to-b from-transparent to-canvas" />
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_70%_55%_at_22%_38%,var(--hz-veil),transparent_70%)]" />
    </div>
  );
}
