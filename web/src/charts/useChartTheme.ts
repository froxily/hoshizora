import { useMemo } from 'react';
import { chartTheme, type ChartTheme } from './theme';

export function useChartTheme(): ChartTheme {
  return useMemo(() => chartTheme(), []);
}
