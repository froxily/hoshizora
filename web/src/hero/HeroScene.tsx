import { Canvas, useFrame } from '@react-three/fiber';
import { useEffect, useMemo } from 'react';
import { PerspectiveCamera } from 'three';
import { createNebula, createPlanet, createStarfield, tokenColor, type SceneBody } from './bodies';
import { currentParallax, stepParallax, trackParallax } from './parallax';
import type { HeroQuality } from './quality';

const POINTER_SHIFT_X = 1.4;
const POINTER_SHIFT_Y = 0.8;
const SCROLL_SHIFT_PER_PIXEL = 0.0035;
const LANDSCAPE_FOV = 45;
const PORTRAIT_FOV = 58;

function Body({ create }: { create: () => SceneBody }) {
  const body = useMemo(() => create(), [create]);

  useEffect(
    () => () => {
      body.dispose();
    },
    [body],
  );

  useFrame((state, delta) => {
    const parallax = currentParallax();
    body.update({
      elapsed: state.clock.elapsedTime,
      delta,
      pixelRatio: state.viewport.dpr,
      width: state.size.width,
      height: state.size.height,
      parallax: parallax.pointer,
    });
  });

  return <primitive object={body.object} />;
}

function CameraRig({ parallax }: { parallax: boolean }) {
  useEffect(() => (parallax ? trackParallax() : undefined), [parallax]);

  useFrame((state, delta) => {
    const camera = state.camera;
    if (camera instanceof PerspectiveCamera) {
      const fov = state.size.width < state.size.height ? PORTRAIT_FOV : LANDSCAPE_FOV;
      if (camera.fov !== fov) {
        camera.fov = fov;
        camera.updateProjectionMatrix();
      }
    }
    const { pointer, scrollY } = stepParallax(delta);
    camera.position.set(
      pointer.x * POINTER_SHIFT_X,
      -pointer.y * POINTER_SHIFT_Y - scrollY * SCROLL_SHIFT_PER_PIXEL,
      0,
    );
  });

  return null;
}

export interface HeroSceneProps {
  readonly animate: boolean;
  readonly quality: HeroQuality;
  readonly onReady: () => void;
}

export default function HeroScene({ animate, quality, onReady }: HeroSceneProps) {
  const nebula = useMemo(() => () => createNebula(quality.octaves), [quality.octaves]);
  const stars = useMemo(() => () => createStarfield(quality.stars), [quality.stars]);

  return (
    <Canvas
      dpr={[1, quality.maxDpr]}
      frameloop={animate ? 'always' : 'demand'}
      gl={{ antialias: true, powerPreference: 'low-power', alpha: false }}
      camera={{ fov: LANDSCAPE_FOV, near: 0.1, far: 200, position: [0, 0, 0] }}
      onCreated={({ gl }) => {
        gl.setClearColor(tokenColor('--hz-canvas'));
        requestAnimationFrame(onReady);
      }}
      aria-hidden
    >
      <CameraRig parallax={animate} />
      <Body create={nebula} />
      <Body create={stars} />
      <Body create={createPlanet} />
    </Canvas>
  );
}
