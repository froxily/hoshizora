import { useSyncExternalStore } from 'react';

export type MotionChoice = 'full' | 'reduced';

export const MOTION_STORAGE_KEY = 'hoshizora.motion';

const REDUCED_QUERY = '(prefers-reduced-motion: reduce)';

const listeners = new Set<() => void>();

let sessionChoice: MotionChoice | null = null;

function isMotionChoice(value: string | null): value is MotionChoice {
  return value === 'full' || value === 'reduced';
}

export function readStoredMotion(): MotionChoice | null {
  try {
    const stored = window.localStorage.getItem(MOTION_STORAGE_KEY);
    return isMotionChoice(stored) ? stored : null;
  } catch {
    return null;
  }
}

function persistMotion(choice: MotionChoice): boolean {
  try {
    window.localStorage.setItem(MOTION_STORAGE_KEY, choice);
    return true;
  } catch {
    return false;
  }
}

function reducedMotionQuery(): MediaQueryList | null {
  return typeof window.matchMedia === 'function' ? window.matchMedia(REDUCED_QUERY) : null;
}

export function resolveMotion(): MotionChoice {
  return (
    sessionChoice ??
    readStoredMotion() ??
    (reducedMotionQuery()?.matches === true ? 'reduced' : 'full')
  );
}

export function applyMotion(choice: MotionChoice = resolveMotion()): void {
  document.documentElement.dataset.motion = choice;
}

function notify(): void {
  listeners.forEach((listener) => {
    listener();
  });
}

export function chooseMotion(choice: MotionChoice): void {
  sessionChoice = choice;
  persistMotion(choice);
  applyMotion(choice);
  notify();
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  const media = reducedMotionQuery();
  const onSystemChange = () => {
    applyMotion();
    listener();
  };
  media?.addEventListener('change', onSystemChange);
  return () => {
    listeners.delete(listener);
    media?.removeEventListener('change', onSystemChange);
  };
}

export function useMotion(): MotionChoice {
  return useSyncExternalStore(subscribe, resolveMotion);
}

export function useReducedMotion(): boolean {
  return useMotion() === 'reduced';
}
