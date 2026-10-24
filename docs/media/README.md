# README media

Screenshots and the demo GIF of Hoshizora's own interface, captured from the live preview (<https://hoshizorapreview.z48.web.core.windows.net>) by `just readme-media` (`web/scripts/readme-media.ts`, Playwright in Chromium, converted with cwebp and ffmpeg).

| File | Page | Viewport |
|---|---|---|
| `tour.gif` | Home in English, the switch to Japanese, then the Sun page | 1280 × 720, shown at 800 px, 10 fps |
| `home-en.webp` | Home, English | 1440 × 900 |
| `home-ja-phone.webp` | Home, Japanese | Pixel 7 |
| `launches-en.webp` | Launches per year by national program | 1440 × 900 |
| `near-earth-ja.webp` | Near-Earth facts, Japanese | 1440 × 900 |
| `sun-ja.webp` | Aurora forecast, Japanese, times in JST | 1440 × 900 |
| `agency-jaxa-ja.webp` | JAXA profile, Japanese | 1440 × 900 |

## Provenance and license

- Everything in the frames is original to this project: the procedural starfield, planet and nebula shaders, the layout and the charts. No photography, film, anime, game or agency artwork appears.
- The fonts are M PLUS 1 and IBM Plex Sans JP under the SIL Open Font License 1.1, credited in `web/src/assets/credits.json` and on the Sources & Credits page.
- The data comes from Launch Library 2, CelesTrak, NASA/JPL, NOAA SWPC and the NASA Exoplanet Archive, each credited on the Sources & Credits page.
- Captured 2026-10-24. They show the data of that day, so re-run `just readme-media` after visible changes.
