import { useSyncExternalStore } from 'react';

export type DataLinkStatus = 'idle' | 'connected' | 'waking' | 'offline';

export interface DataLinkState {
  readonly status: DataLinkStatus;
  readonly since: number | null;
}

export const SLOW_RESPONSE_MS = 3_000;
export const WAKE_WINDOW_MS = 180_000;

const listeners = new Set<() => void>();

let state: DataLinkState = { status: 'idle', since: null };
let offlineTimer: ReturnType<typeof setTimeout> | null = null;

function publish(next: DataLinkState): void {
  if (next.status === state.status && next.since === state.since) {
    return;
  }
  state = next;
  listeners.forEach((listener) => {
    listener();
  });
}

function clearOfflineTimer(): void {
  if (offlineTimer !== null) {
    clearTimeout(offlineTimer);
    offlineTimer = null;
  }
}

export function markConnected(): void {
  clearOfflineTimer();
  publish({ status: 'connected', since: null });
}

export function markWaking(now: number = Date.now()): void {
  if (state.status === 'waking' || state.status === 'offline') {
    return;
  }
  publish({ status: 'waking', since: now });
  clearOfflineTimer();
  offlineTimer = setTimeout(() => {
    publish({ status: 'offline', since: state.since });
  }, WAKE_WINDOW_MS);
}

export function resetDataLink(): void {
  clearOfflineTimer();
  publish({ status: 'idle', since: null });
}

export function dataLinkState(): DataLinkState {
  return state;
}

export function subscribeDataLink(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useDataLink(): DataLinkState {
  return useSyncExternalStore(subscribeDataLink, dataLinkState);
}
