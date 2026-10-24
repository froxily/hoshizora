# ADR 0008: Frontend architecture

Status: accepted (Phase 4, 2026-10-18)

## Context

- The MVP pages read a read-only API that, on a free host, can sleep and take about a minute to wake.
- The design calls for a cinematic 3D hero, yet the Lighthouse budget is 80 on mobile and 95 on desktop for performance, and 95 for accessibility.
- Every number must show its source and date, and every chart needs a table view.
- Japanese web fonts are large even when sliced.

## Decision

1. **Client-rendered SPA with route-level code splitting.** Home is in the main bundle; the other pages, the hero scene and ECharts are separate chunks. Route loaders prefetch each page's first queries in parallel with its chunk.
2. **The data link is explicit state, not an error.** Transient failures (network, timeout, 502/503/504, a non-JSON wake page) move the app to `waking`, and the UI says so in a designed panel while every region keeps its layout. TanStack Query retries those failures without limit, with capped backoff. Only real API errors show an error panel.
3. **3D only where it is cheap.** The hero loads after `load` and idle time, behind a matching SVG poster. It is skipped on software WebGL, where it would block the main thread for seconds. The same check makes the no-WebGL fallback the tested path in Playwright.
4. **Presentation is a web concern.** The API stores and renders fact text. The web maps template keys to a key figure and a comparison scale in `presentation.ts`, guarded by a test against `facts/templates/*.yaml`. The template format and the API stay unchanged.
5. **CSS animations instead of Motion.** Reveals, rises and pulses are a few token-driven keyframes, honoring both `prefers-reduced-motion` and the in-app toggle. The `motion` package was dropped, because it added weight without a use.
6. **Fonts after the first frame.** M PLUS 1 and IBM Plex Sans JP load from an effect two animation frames after the first render. Text first paints in the system fallback and swaps. This took Home from 82 to 97 on mobile.
7. **Weak ETags.** The API's body-hash ETag is weak so Tomcat can gzip JSON. The aurora grid drops from 225 KB to 42 KB.

## Consequences

- First paint still needs the main bundle (about 107 KB gzipped). Prerendering static HTML per route would cut mobile FCP further and help sharing previews; that is a later option, not a requirement.
- Fonts swap after first paint, so for a moment text shows in the system face. The fallback stacks are chosen to keep the swap free of measurable layout shift.
- Lighthouse in this repo runs against `vite preview` with the local API (`just web-preview`, `just lighthouse`). On 2026-10-18, mobile performance was 87–97, desktop 100 and accessibility 100 on every page.
