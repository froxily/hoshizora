import type { StarLayer } from './bodies';

export interface HeroQuality {
  readonly stars: readonly StarLayer[];
  readonly octaves: number;
  readonly maxDpr: number;
}

interface DeviceHints {
  readonly cores: number;
  readonly memoryGb: number | undefined;
  readonly coarsePointer: boolean;
  readonly viewportWidth: number;
}

const FAR: StarLayer = {
  count: 3_600,
  nearest: 85,
  depth: 30,
  size: 1.1,
  sizeSpread: 2.6,
  brightness: 0.85,
  seed: 1957,
};
const MID: StarLayer = {
  count: 1_400,
  nearest: 50,
  depth: 20,
  size: 1.6,
  sizeSpread: 3.2,
  brightness: 1,
  seed: 1961,
};
const NEAR: StarLayer = {
  count: 260,
  nearest: 24,
  depth: 12,
  size: 2.2,
  sizeSpread: 4.2,
  brightness: 1.15,
  seed: 1969,
};

function scaled(factor: number): StarLayer[] {
  return [FAR, MID, NEAR].map((layer) => ({
    ...layer,
    count: Math.round(layer.count * factor),
  }));
}

const FULL: HeroQuality = { stars: scaled(1), octaves: 5, maxDpr: 1.5 };
const BALANCED: HeroQuality = { stars: scaled(0.6), octaves: 4, maxDpr: 1.25 };
const LOW: HeroQuality = { stars: scaled(0.4), octaves: 3, maxDpr: 1 };

export function chooseQuality(hints: DeviceHints): HeroQuality {
  const lowEnd = hints.cores <= 4 || (hints.memoryGb !== undefined && hints.memoryGb <= 4);
  if (lowEnd) {
    return LOW;
  }
  return hints.coarsePointer || hints.viewportWidth < 768 ? BALANCED : FULL;
}

export function deviceHints(): DeviceHints {
  const memory = (navigator as Navigator & { deviceMemory?: number }).deviceMemory;
  return {
    cores: navigator.hardwareConcurrency,
    memoryGb: memory,
    coarsePointer:
      typeof window.matchMedia === 'function' && window.matchMedia('(pointer: coarse)').matches,
    viewportWidth: window.innerWidth,
  };
}

const SOFTWARE_RENDERERS = /swiftshader|llvmpipe|softpipe|software|basic render/i;

export function isSoftwareRenderer(renderer: string): boolean {
  return SOFTWARE_RENDERERS.test(renderer);
}

export function supportsWebGl(): boolean {
  try {
    const context = document.createElement('canvas').getContext('webgl2');
    if (context === null) {
      return false;
    }
    const info = context.getExtension('WEBGL_debug_renderer_info');
    const renderer =
      info === null ? '' : String(context.getParameter(info.UNMASKED_RENDERER_WEBGL));
    context.getExtension('WEBGL_lose_context')?.loseContext();
    return !isSoftwareRenderer(renderer);
  } catch {
    return false;
  }
}
