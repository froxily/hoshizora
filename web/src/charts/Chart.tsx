import { useEffect, useRef, useState } from 'react';
import { useReducedMotion } from '../motion/motion';
import { echarts, type ChartOption } from './echarts';

interface ChartProps {
  readonly option: ChartOption;
  readonly height: number;
  readonly label: string;
}

export function Chart({ option, height, label }: ChartProps) {
  const container = useRef<HTMLDivElement>(null);
  const instance = useRef<ReturnType<typeof echarts.init> | null>(null);
  const reduced = useReducedMotion();
  const [fontLoads, setFontLoads] = useState(0);

  useEffect(() => {
    const element = container.current;
    if (element === null) {
      return;
    }
    const chart = echarts.init(element, undefined, { renderer: 'svg' });
    instance.current = chart;
    const observer = new ResizeObserver(() => {
      chart.resize();
    });
    observer.observe(element);
    const onFontsLoaded = () => {
      setFontLoads((count) => count + 1);
    };
    document.fonts.addEventListener('loadingdone', onFontsLoaded);
    return () => {
      document.fonts.removeEventListener('loadingdone', onFontsLoaded);
      observer.disconnect();
      chart.dispose();
      instance.current = null;
    };
  }, []);

  useEffect(() => {
    instance.current?.setOption(
      { animation: !reduced, animationDuration: 700, animationEasing: 'cubicOut', ...option },
      true,
    );
  }, [option, reduced, fontLoads]);

  return (
    <div ref={container} role="img" aria-label={label} style={{ height }} className="w-full" />
  );
}
