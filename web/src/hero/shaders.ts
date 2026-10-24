const NOISE_2D = /* glsl */ `
float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
}

float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
    mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x),
    u.y
  );
}

float fbm(vec2 p, int octaves) {
  float value = 0.0;
  float amplitude = 0.5;
  for (int i = 0; i < 6; i++) {
    if (i >= octaves) break;
    value += amplitude * noise(p);
    p = p * 2.03 + vec2(1.7, 9.2);
    amplitude *= 0.5;
  }
  return value;
}
`;

const NOISE_3D = /* glsl */ `
float hash3(vec3 p) {
  p = fract(p * 0.3183099 + 0.1);
  p *= 17.0;
  return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float noise3(vec3 p) {
  vec3 i = floor(p);
  vec3 f = fract(p);
  vec3 u = f * f * (3.0 - 2.0 * f);
  return mix(
    mix(
      mix(hash3(i), hash3(i + vec3(1.0, 0.0, 0.0)), u.x),
      mix(hash3(i + vec3(0.0, 1.0, 0.0)), hash3(i + vec3(1.0, 1.0, 0.0)), u.x),
      u.y
    ),
    mix(
      mix(hash3(i + vec3(0.0, 0.0, 1.0)), hash3(i + vec3(1.0, 0.0, 1.0)), u.x),
      mix(hash3(i + vec3(0.0, 1.0, 1.0)), hash3(i + vec3(1.0, 1.0, 1.0)), u.x),
      u.y
    ),
    u.z
  );
}

float fbm3(vec3 p) {
  float value = 0.0;
  float amplitude = 0.5;
  for (int i = 0; i < 5; i++) {
    value += amplitude * noise3(p);
    p = p * 2.07 + vec3(3.1, 1.7, 5.3);
    amplitude *= 0.5;
  }
  return value;
}
`;

export const starVertex = /* glsl */ `
uniform float uTime;
uniform float uPixelRatio;
uniform float uBrightness;
attribute float aSize;
attribute float aPhase;
attribute float aTint;
varying float vAlpha;
varying float vTint;

void main() {
  vec4 viewPosition = modelViewMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * viewPosition;
  float twinkle = 0.8 + 0.2 * sin(uTime * (0.35 + aPhase * 0.6) + aPhase * 6.2831);
  vAlpha = twinkle * uBrightness;
  vTint = aTint;
  gl_PointSize = aSize * uPixelRatio;
}
`;

export const starFragment = /* glsl */ `
varying float vAlpha;
varying float vTint;

void main() {
  float radius = length(gl_PointCoord - 0.5);
  float core = smoothstep(0.5, 0.0, radius);
  float alpha = (pow(core, 3.0) + 0.25 * pow(core, 1.2)) * vAlpha;
  vec3 cool = vec3(0.82, 0.93, 1.0);
  vec3 warm = vec3(1.0, 0.87, 0.72);
  gl_FragColor = vec4(mix(cool, warm, vTint), alpha);
}
`;

export const backdropVertex = /* glsl */ `
varying vec2 vUv;

void main() {
  vUv = uv;
  gl_Position = vec4(position.xy, 0.9999, 1.0);
}
`;

export const nebulaFragment = /* glsl */ `
uniform float uTime;
uniform vec2 uResolution;
uniform vec2 uOffset;
uniform int uOctaves;
varying vec2 vUv;
${NOISE_2D}

void main() {
  vec2 p = (vUv - 0.5 + uOffset) * vec2(uResolution.x / uResolution.y, 1.0) * 2.4;
  float t = uTime * 0.01;
  vec2 warp = vec2(fbm(p + t, uOctaves), fbm(p + vec2(5.2, 1.3) - t, uOctaves));
  float density = fbm(p + 1.8 * warp + vec2(t * 0.5, 0.0), uOctaves);
  float band = exp(-pow((p.y - 0.32 * p.x - 0.55) * 1.5, 2.0));
  float cloud = smoothstep(0.38, 0.95, density) * band;
  vec3 deep = vec3(0.016, 0.022, 0.040);
  vec3 cyan = vec3(0.30, 0.56, 0.64);
  vec3 amber = vec3(0.58, 0.40, 0.22);
  vec3 color = deep * (0.55 + 0.9 * band)
    + cyan * cloud * 0.12
    + amber * cloud * cloud * warp.x * 0.12;
  float vignette = smoothstep(1.9, 0.3, length(p * vec2(0.55, 1.0)));
  gl_FragColor = vec4(color * vignette, 1.0);
}
`;

export const bodyVertex = /* glsl */ `
varying vec3 vNormal;
varying vec3 vWorldPosition;
varying vec3 vObjectPosition;

void main() {
  vObjectPosition = position;
  vec4 world = modelMatrix * vec4(position, 1.0);
  vWorldPosition = world.xyz;
  vNormal = normalize(mat3(modelMatrix) * normal);
  gl_Position = projectionMatrix * viewMatrix * world;
}
`;

export const planetFragment = /* glsl */ `
uniform vec3 uLightDirection;
uniform vec3 uRim;
uniform vec3 uHaze;
uniform float uRadius;
varying vec3 vNormal;
varying vec3 vWorldPosition;
varying vec3 vObjectPosition;
${NOISE_3D}

void main() {
  vec3 normal = normalize(vNormal);
  vec3 view = normalize(cameraPosition - vWorldPosition);
  vec3 surfacePoint = vObjectPosition / uRadius;

  float continents = fbm3(surfacePoint * 2.6);
  float detail = fbm3(surfacePoint * 9.0 + 4.0);
  float land = smoothstep(0.46, 0.56, continents + 0.12 * (detail - 0.5));
  vec3 basin = vec3(0.045, 0.060, 0.075);
  vec3 plain = mix(vec3(0.165, 0.145, 0.125), vec3(0.25, 0.21, 0.17), detail);
  vec3 ground = mix(basin, plain, land);

  float streaks = fbm3(vec3(surfacePoint.x * 3.0, surfacePoint.y * 14.0, surfacePoint.z * 3.0) + 11.0);
  float clouds = smoothstep(0.55, 0.78, streaks) * 0.55;
  ground = mix(ground, vec3(0.62, 0.62, 0.64), clouds);

  float light = dot(normal, uLightDirection);
  float day = smoothstep(-0.12, 0.45, light);
  vec3 lit = ground * (0.05 + 0.78 * day);
  vec3 night = ground * 0.035;
  vec3 color = mix(night, lit, day);

  float rim = 1.0 - max(dot(normal, view), 0.0);
  float sunward = smoothstep(-0.3, 0.5, light);
  vec3 dusty = mix(uRim, vec3(dot(uRim, vec3(0.3333))), 0.3);
  vec3 atmosphere = mix(uHaze * 0.35, dusty, sunward) * pow(rim, 4.0) * (0.04 + 0.55 * sunward);
  gl_FragColor = vec4(color + atmosphere, 1.0);
}
`;

export const atmosphereFragment = /* glsl */ `
uniform vec3 uLightDirection;
uniform vec3 uRim;
uniform vec3 uHaze;
uniform float uThickness;
varying vec3 vNormal;
varying vec3 vWorldPosition;

void main() {
  vec3 normal = normalize(vNormal);
  vec3 view = normalize(cameraPosition - vWorldPosition);
  float depth = clamp(-dot(normal, view) / uThickness, 0.0, 1.0);
  float glow = pow(depth, 3.0);
  float sunward = smoothstep(-0.3, 0.55, dot(normal, uLightDirection));
  vec3 dusty = mix(uRim, vec3(dot(uRim, vec3(0.3333))), 0.35);
  vec3 color = mix(uHaze * 0.7, dusty, sunward);
  gl_FragColor = vec4(color, glow * (0.06 + 0.42 * sunward));
}
`;
