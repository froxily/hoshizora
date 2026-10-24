interface PosterStar {
  readonly x: number;
  readonly y: number;
  readonly r: number;
  readonly o: number;
}

function posterStars(count: number): PosterStar[] {
  let state = 2003;
  const random = () => {
    state = (state * 1_664_525 + 1_013_904_223) % 4_294_967_296;
    return state / 4_294_967_296;
  };
  return Array.from({ length: count }, () => ({
    x: Math.round(random() * 1600),
    y: Math.round(random() * 640),
    r: 0.5 + Math.pow(random(), 6) * 1.9,
    o: 0.3 + random() * 0.65,
  }));
}

const STARS = posterStars(260);
const PLANET = { cx: 800, cy: 1908, r: 1287 };

export function HeroPoster() {
  return (
    <svg
      className="absolute inset-0 h-full w-full"
      viewBox="0 0 1600 900"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden
      focusable="false"
    >
      <defs>
        <radialGradient id="hz-poster-nebula" cx="0.7" cy="0.25" r="0.6">
          <stop offset="0" className="[stop-color:var(--hz-cyan)]" stopOpacity="0.08" />
          <stop offset="1" className="[stop-color:var(--hz-canvas)]" stopOpacity="0" />
        </radialGradient>
        <radialGradient id="hz-poster-day" cx="0.3" cy="0.02" r="0.32">
          <stop
            offset="0"
            className="[stop-color:color-mix(in_oklab,var(--hz-amber)_30%,var(--hz-canvas))]"
          />
          <stop
            offset="0.55"
            className="[stop-color:color-mix(in_oklab,var(--hz-amber)_10%,var(--hz-canvas))]"
          />
          <stop offset="1" className="[stop-color:var(--hz-canvas)]" />
        </radialGradient>
        <linearGradient id="hz-poster-rim" x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" className="[stop-color:var(--hz-amber)]" stopOpacity="0.35" />
          <stop offset="0.32" className="[stop-color:var(--hz-amber)]" stopOpacity="0.95" />
          <stop offset="0.68" className="[stop-color:var(--hz-cyan)]" stopOpacity="0.4" />
          <stop offset="1" className="[stop-color:var(--hz-cyan)]" stopOpacity="0.1" />
        </linearGradient>
        <filter id="hz-poster-glow" x="-10%" y="-10%" width="120%" height="120%">
          <feGaussianBlur stdDeviation="12" />
        </filter>
      </defs>
      <rect width="1600" height="900" className="fill-canvas" />
      <rect width="1600" height="900" fill="url(#hz-poster-nebula)" />
      <g className="fill-ink">
        {STARS.map((star) => (
          <circle
            key={`${String(star.x)}-${String(star.y)}`}
            cx={star.x}
            cy={star.y}
            r={star.r}
            opacity={star.o}
          />
        ))}
      </g>
      <circle
        cx={PLANET.cx}
        cy={PLANET.cy}
        r={PLANET.r + 8}
        fill="none"
        stroke="url(#hz-poster-rim)"
        strokeWidth="22"
        opacity="0.45"
        filter="url(#hz-poster-glow)"
      />
      <circle cx={PLANET.cx} cy={PLANET.cy} r={PLANET.r} fill="url(#hz-poster-day)" />
      <circle
        cx={PLANET.cx}
        cy={PLANET.cy}
        r={PLANET.r}
        fill="none"
        stroke="url(#hz-poster-rim)"
        strokeWidth="1.8"
      />
    </svg>
  );
}
