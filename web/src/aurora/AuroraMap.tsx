import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { chartTheme } from '../charts/theme';
import { EDGE_LATITUDE, PLACES, project, type Hemisphere } from './projection';

const RINGS = [80, 70, 60, 50];
const FULL_SCALE_PERCENT = 40;
const MAX_SIZE = 560;

interface AuroraMapProps {
  readonly cells: readonly (readonly number[])[];
  readonly hemisphere: Hemisphere;
}

function mix(low: string, high: string, share: number): string {
  const parse = (hex: string) =>
    [1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16));
  const [a, b] = [parse(low), parse(high)];
  const channel = (index: number) =>
    Math.round((a[index] ?? 0) + ((b[index] ?? 0) - (a[index] ?? 0)) * share);
  return `rgb(${String(channel(0))} ${String(channel(1))} ${String(channel(2))})`;
}

export function AuroraMap({ cells, hemisphere }: AuroraMapProps) {
  const { t } = useTranslation();
  const canvas = useRef<HTMLCanvasElement>(null);
  const frame = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState(0);

  useEffect(() => {
    const element = frame.current;
    if (element === null) {
      return;
    }
    const observer = new ResizeObserver(([entry]) => {
      setSize(Math.min(MAX_SIZE, Math.floor(entry?.contentRect.width ?? MAX_SIZE)));
    });
    observer.observe(element);
    return () => {
      observer.disconnect();
    };
  }, []);

  useEffect(() => {
    const element = canvas.current;
    const context = element?.getContext('2d');
    if (element === null || context === null || context === undefined || size === 0) {
      return;
    }
    const theme = chartTheme();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    element.width = size * ratio;
    element.height = size * ratio;
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, size, size);
    const center = size / 2;
    const radius = center - 28;
    const step = radius / (90 - EDGE_LATITUDE);

    context.strokeStyle = theme.hairline;
    context.lineWidth = 1;
    for (const latitude of [...RINGS, EDGE_LATITUDE]) {
      context.beginPath();
      context.arc(center, center, (90 - latitude) * step, 0, Math.PI * 2);
      context.stroke();
    }
    for (const longitude of [0, 90, 180, 270]) {
      const edge = project(
        longitude,
        hemisphere === 'north' ? EDGE_LATITUDE : -EDGE_LATITUDE,
        hemisphere,
        radius,
      );
      if (edge !== null) {
        context.beginPath();
        context.moveTo(center, center);
        context.lineTo(center + edge.x, center + edge.y);
        context.stroke();
      }
    }

    for (const [longitude = 0, latitude = 0, percent = 0] of cells) {
      const point = project(longitude, latitude, hemisphere, radius);
      if (point === null) {
        continue;
      }
      const share = Math.min(1, percent / FULL_SCALE_PERCENT);
      context.fillStyle = mix(theme.rampLow, theme.rampHigh, share);
      context.globalAlpha = 0.35 + 0.65 * share;
      context.beginPath();
      context.arc(center + point.x, center + point.y, Math.max(1, step * 0.55), 0, Math.PI * 2);
      context.fill();
    }
    context.globalAlpha = 1;

    context.font = `12px ${theme.font}`;
    context.fillStyle = theme.muted;
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    const labels: [number, string][] = [
      [0, '0°'],
      [90, '90°E'],
      [180, '180°'],
      [270, '90°W'],
    ];
    for (const [longitude, label] of labels) {
      const point = project(
        longitude,
        hemisphere === 'north' ? EDGE_LATITUDE - 3 : -(EDGE_LATITUDE - 3),
        hemisphere,
        radius + 14,
      );
      if (point !== null) {
        context.fillText(label, center + point.x, center + point.y);
      }
    }
    for (const latitude of RINGS) {
      context.fillText(`${String(latitude)}°`, center + 4, center - (90 - latitude) * step - 8);
    }

    for (const place of PLACES) {
      const point = project(place.longitude, place.latitude, hemisphere, radius);
      if (point === null) {
        continue;
      }
      context.fillStyle = theme.warm;
      context.beginPath();
      context.arc(center + point.x, center + point.y, 3.5, 0, Math.PI * 2);
      context.fill();
      context.fillStyle = theme.ink;
      context.textAlign = point.x > 0 ? 'left' : 'right';
      context.fillText(
        t(`places.${place.key}`),
        center + point.x + (point.x > 0 ? 8 : -8),
        center + point.y,
      );
    }
  }, [cells, hemisphere, size, t]);

  return (
    <div ref={frame} className="w-full max-w-[560px]">
      <canvas
        ref={canvas}
        role="img"
        aria-label={t('sun.aurora.mapLabel', { hemisphere: t(`sun.aurora.${hemisphere}`) })}
        className="aspect-square w-full"
      />
    </div>
  );
}
