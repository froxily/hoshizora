import { describe, expect, it } from 'vitest';
import { chooseQuality, isSoftwareRenderer } from './quality';

describe('hero quality', () => {
  it.each([
    'ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero)), SwiftShader driver)',
    'llvmpipe (LLVM 17.0.6, 256 bits)',
    'ANGLE (Microsoft, Microsoft Basic Render Driver Direct3D11)',
  ])('treats %s as software rendering', (renderer) => {
    expect(isSoftwareRenderer(renderer)).toBe(true);
  });

  it('keeps hardware renderers', () => {
    expect(
      isSoftwareRenderer('ANGLE (Apple, ANGLE Metal Renderer: Apple M2, Unspecified Version)'),
    ).toBe(false);
  });

  it('lowers quality on small or low-memory devices', () => {
    const desktop = chooseQuality({
      cores: 8,
      memoryGb: 16,
      coarsePointer: false,
      viewportWidth: 1440,
    });
    const phone = chooseQuality({ cores: 8, memoryGb: 8, coarsePointer: true, viewportWidth: 390 });
    const lowEnd = chooseQuality({
      cores: 4,
      memoryGb: 2,
      coarsePointer: true,
      viewportWidth: 360,
    });
    expect(desktop.maxDpr).toBeGreaterThan(phone.maxDpr);
    expect(phone.maxDpr).toBeGreaterThan(lowEnd.maxDpr);
  });
});
