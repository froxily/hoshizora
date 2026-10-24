import { Vector2 } from 'three';

const POINTER_EASE_PER_SECOND = 2.5;

const pointer = new Vector2();
const smoothed = new Vector2();
let scrollY = 0;

export function trackParallax(): () => void {
  const onPointer = (event: PointerEvent) => {
    if (event.pointerType === 'mouse') {
      pointer.set(
        (event.clientX / window.innerWidth) * 2 - 1,
        (event.clientY / window.innerHeight) * 2 - 1,
      );
    }
  };
  const onScroll = () => {
    scrollY = window.scrollY;
  };
  onScroll();
  window.addEventListener('pointermove', onPointer, { passive: true });
  window.addEventListener('scroll', onScroll, { passive: true });
  return () => {
    window.removeEventListener('pointermove', onPointer);
    window.removeEventListener('scroll', onScroll);
    pointer.set(0, 0);
    smoothed.set(0, 0);
    scrollY = 0;
  };
}

export interface ParallaxState {
  readonly pointer: Vector2;
  readonly scrollY: number;
}

export function stepParallax(delta: number): ParallaxState {
  smoothed.lerp(pointer, Math.min(1, delta * POINTER_EASE_PER_SECOND));
  return currentParallax();
}

export function currentParallax(): ParallaxState {
  return { pointer: smoothed, scrollY };
}
