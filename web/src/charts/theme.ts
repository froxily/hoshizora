const SERIES_COUNT = 6;

function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

export interface ChartTheme {
  readonly ink: string;
  readonly muted: string;
  readonly faint: string;
  readonly hairline: string;
  readonly surface: string;
  readonly canvas: string;
  readonly warm: string;
  readonly cool: string;
  readonly series: readonly string[];
  readonly other: string;
  readonly rampLow: string;
  readonly rampHigh: string;
  readonly font: string;
}

export function chartTheme(): ChartTheme {
  return {
    ink: token('--hz-ink'),
    muted: token('--hz-ink-muted'),
    faint: token('--hz-ink-faint'),
    hairline: token('--hz-hairline'),
    surface: token('--hz-surface-raised'),
    canvas: token('--hz-canvas'),
    warm: token('--hz-mark-warm'),
    cool: token('--hz-mark-cool'),
    series: Array.from({ length: SERIES_COUNT }, (_, index) =>
      token(`--hz-series-${String(index + 1)}`),
    ),
    other: token('--hz-series-other'),
    rampLow: token('--hz-ramp-low'),
    rampHigh: token('--hz-ramp-high'),
    font: token('--hz-font-text'),
  };
}

export function seriesColor(theme: ChartTheme, index: number): string {
  return theme.series[index] ?? theme.other;
}

export function axisStyle(theme: ChartTheme) {
  return {
    axisLine: { lineStyle: { color: theme.hairline } },
    axisTick: { show: false },
    axisLabel: { color: theme.muted, fontSize: 12, fontFamily: theme.font },
    splitLine: { lineStyle: { color: theme.hairline, type: 'dashed' as const } },
    nameTextStyle: { color: theme.muted, fontSize: 12 },
  };
}

export function baseOption(theme: ChartTheme) {
  return {
    backgroundColor: 'transparent',
    textStyle: { fontFamily: theme.font, color: theme.muted },
    grid: { left: 8, right: 16, top: 32, bottom: 8, containLabel: true },
    tooltip: {
      backgroundColor: theme.surface,
      borderColor: theme.hairline,
      textStyle: { color: theme.ink, fontSize: 13, fontFamily: theme.font },
      extraCssText: 'border-radius: 4px; box-shadow: none;',
    },
    legend: {
      show: false,
      textStyle: { color: theme.muted, fontSize: 12 },
      icon: 'roundRect',
      itemWidth: 10,
      itemHeight: 10,
      top: 0,
      left: 0,
    },
  };
}
