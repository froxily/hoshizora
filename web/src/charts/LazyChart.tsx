import { lazy, Suspense } from 'react';
import type { ChartOption } from './echarts';

const Chart = lazy(async () => ({ default: (await import('./Chart')).Chart }));

interface LazyChartProps {
  readonly option: ChartOption;
  readonly height: number;
  readonly label: string;
}

export function LazyChart({ option, height, label }: LazyChartProps) {
  return (
    <Suspense
      fallback={<div style={{ height }} className="w-full rounded bg-surface/40" aria-hidden />}
    >
      <Chart option={option} height={height} label={label} />
    </Suspense>
  );
}
