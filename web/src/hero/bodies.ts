import {
  AdditiveBlending,
  BackSide,
  BufferAttribute,
  BufferGeometry,
  Color,
  Group,
  Mesh,
  PlaneGeometry,
  Points,
  ShaderMaterial,
  SphereGeometry,
  Vector2,
  Vector3,
  type Object3D,
} from 'three';
import {
  atmosphereFragment,
  backdropVertex,
  bodyVertex,
  nebulaFragment,
  planetFragment,
  starFragment,
  starVertex,
} from './shaders';

export interface FrameInfo {
  readonly elapsed: number;
  readonly delta: number;
  readonly pixelRatio: number;
  readonly width: number;
  readonly height: number;
  readonly parallax: Vector2;
}

export interface SceneBody {
  readonly object: Object3D;
  update(frame: FrameInfo): void;
  dispose(): void;
}

export interface StarLayer {
  readonly count: number;
  readonly nearest: number;
  readonly depth: number;
  readonly size: number;
  readonly sizeSpread: number;
  readonly brightness: number;
  readonly seed: number;
}

const PLANET_RADIUS = 40;
const PLANET_ANGULAR_RADIUS = (60 * Math.PI) / 180;
const PLANET_CENTER_BELOW = (69 * Math.PI) / 180;
const PLANET_DISTANCE = PLANET_RADIUS / Math.sin(PLANET_ANGULAR_RADIUS);
const PLANET_CENTER = new Vector3(
  0,
  -PLANET_DISTANCE * Math.sin(PLANET_CENTER_BELOW),
  -PLANET_DISTANCE * Math.cos(PLANET_CENTER_BELOW),
);
const PLANET_SPIN_RADIANS_PER_SECOND = 0.012;
const ATMOSPHERE_SCALE = 1.02;
const ATMOSPHERE_THICKNESS = Math.sqrt(1 - 1 / (ATMOSPHERE_SCALE * ATMOSPHERE_SCALE));
const LIGHT_DIRECTION = new Vector3(-0.65, 0.55, -0.15).normalize();
const STAR_DRIFT_RADIANS_PER_SECOND = 0.003;

export function tokenColor(name: string): Color {
  return new Color(getComputedStyle(document.documentElement).getPropertyValue(name).trim());
}

function seededRandom(seed: number): () => number {
  let state = seed;
  return () => {
    state = (state * 1_664_525 + 1_013_904_223) % 4_294_967_296;
    return state / 4_294_967_296;
  };
}

function starGeometry(layer: StarLayer): BufferGeometry {
  const random = seededRandom(layer.seed);
  const positions = new Float32Array(layer.count * 3);
  const sizes = new Float32Array(layer.count);
  const phases = new Float32Array(layer.count);
  const tints = new Float32Array(layer.count);
  for (let index = 0; index < layer.count; index += 1) {
    const z = random() * 2 - 1;
    const angle = random() * Math.PI * 2;
    const ring = Math.sqrt(1 - z * z);
    const distance = layer.nearest + random() * layer.depth;
    positions.set(
      [ring * Math.cos(angle) * distance, z * distance, ring * Math.sin(angle) * distance],
      index * 3,
    );
    sizes[index] = layer.size + Math.pow(random(), 7) * layer.sizeSpread;
    phases[index] = random();
    tints[index] = Math.pow(random(), 2);
  }
  const geometry = new BufferGeometry();
  geometry.setAttribute('position', new BufferAttribute(positions, 3));
  geometry.setAttribute('aSize', new BufferAttribute(sizes, 1));
  geometry.setAttribute('aPhase', new BufferAttribute(phases, 1));
  geometry.setAttribute('aTint', new BufferAttribute(tints, 1));
  return geometry;
}

export function createStarfield(layers: readonly StarLayer[]): SceneBody {
  const uniforms = layers.map((layer) => ({
    uTime: { value: 0 },
    uPixelRatio: { value: 1 },
    uBrightness: { value: layer.brightness },
  }));
  const geometries = layers.map(starGeometry);
  const materials = uniforms.map(
    (layerUniforms) =>
      new ShaderMaterial({
        vertexShader: starVertex,
        fragmentShader: starFragment,
        uniforms: layerUniforms,
        transparent: true,
        depthWrite: false,
        blending: AdditiveBlending,
      }),
  );
  const group = new Group();
  group.rotation.set(0.35, 0, 0.12);
  geometries.forEach((geometry, index) => {
    const material = materials[index];
    if (material !== undefined) {
      group.add(new Points(geometry, material));
    }
  });
  return {
    object: group,
    update: ({ elapsed, delta, pixelRatio }) => {
      uniforms.forEach((layerUniforms) => {
        layerUniforms.uTime.value = elapsed;
        layerUniforms.uPixelRatio.value = pixelRatio;
      });
      group.rotation.y += delta * STAR_DRIFT_RADIANS_PER_SECOND;
    },
    dispose: () => {
      geometries.forEach((geometry) => {
        geometry.dispose();
      });
      materials.forEach((material) => {
        material.dispose();
      });
    },
  };
}

export function createNebula(octaves: number): SceneBody {
  const uniforms = {
    uTime: { value: 0 },
    uResolution: { value: new Vector2(1, 1) },
    uOffset: { value: new Vector2(0, 0) },
    uOctaves: { value: octaves },
  };
  const geometry = new PlaneGeometry(2, 2);
  const material = new ShaderMaterial({
    vertexShader: backdropVertex,
    fragmentShader: nebulaFragment,
    uniforms,
    depthTest: false,
    depthWrite: false,
  });
  const mesh = new Mesh(geometry, material);
  mesh.frustumCulled = false;
  mesh.renderOrder = -1;
  return {
    object: mesh,
    update: ({ elapsed, width, height, parallax }) => {
      uniforms.uTime.value = elapsed;
      uniforms.uResolution.value.set(width, height);
      uniforms.uOffset.value.set(parallax.x * 0.006, parallax.y * 0.006);
    },
    dispose: () => {
      geometry.dispose();
      material.dispose();
    },
  };
}

export function createPlanet(): SceneBody {
  const uniforms = {
    uLightDirection: { value: LIGHT_DIRECTION },
    uRim: { value: tokenColor('--hz-amber') },
    uHaze: { value: tokenColor('--hz-cyan') },
    uRadius: { value: PLANET_RADIUS },
    uThickness: { value: ATMOSPHERE_THICKNESS },
  };
  const surfaceGeometry = new SphereGeometry(PLANET_RADIUS, 160, 120);
  const shellGeometry = new SphereGeometry(PLANET_RADIUS * ATMOSPHERE_SCALE, 160, 120);
  const surface = new ShaderMaterial({
    vertexShader: bodyVertex,
    fragmentShader: planetFragment,
    uniforms,
  });
  const shell = new ShaderMaterial({
    vertexShader: bodyVertex,
    fragmentShader: atmosphereFragment,
    uniforms,
    side: BackSide,
    transparent: true,
    depthWrite: false,
    blending: AdditiveBlending,
  });
  const spin = new Mesh(surfaceGeometry, surface);
  const tilt = new Group();
  tilt.rotation.set(0.55, 0, -0.32);
  tilt.add(spin);
  const group = new Group();
  group.position.copy(PLANET_CENTER);
  group.add(tilt, new Mesh(shellGeometry, shell));
  return {
    object: group,
    update: ({ delta }) => {
      spin.rotation.y += delta * PLANET_SPIN_RADIANS_PER_SECOND;
    },
    dispose: () => {
      surfaceGeometry.dispose();
      shellGeometry.dispose();
      surface.dispose();
      shell.dispose();
    },
  };
}
