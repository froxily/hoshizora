import { useQuery } from '@tanstack/react-query';
import { useState, type CSSProperties } from 'react';
import { useTranslation } from 'react-i18next';
import { factQuery, type Fact } from '../api/queries';
import { figureFor } from '../facts/figure';
import { accentFor, presentationFor } from '../facts/presentation';
import { scaleModel } from '../facts/scale';
import { ScaleBar } from '../facts/ScaleBar';
import { formatDateTime } from '../format/format';
import type { Locale } from '../i18n/locales';
import { useLocale } from '../i18n/useLocale';
import { REVEAL_CLASS, useReveal } from '../motion/useReveal';
import { DataRegion } from './DataRegion';

function Lineage({ id }: { id: number }) {
  const { t } = useTranslation();
  const locale = useLocale();
  const query = useQuery(factQuery(locale, id));

  return (
    <DataRegion query={query} compact>
      {({ fact, lineage }) => (
        <div className="space-y-3 text-xs leading-relaxed text-ink-muted">
          <p>
            {fact.kind.name} · {formatDateTime(locale, fact.generated_at)}
          </p>
          <ul className="space-y-1">
            {fact.sources.map((source) => (
              <li key={`${source.entity}|${source.key}`} className="break-all">
                <span className="text-ink">{source.entity}</span> {source.key}
              </li>
            ))}
          </ul>
          <ul className="space-y-2 border-t border-hairline pt-3">
            {lineage.map((entry) => (
              <li key={entry.content_hash}>
                <span className="text-ink">
                  {t(`source.names.${entry.source}`, { defaultValue: entry.source })}
                </span>{' '}
                · {formatDateTime(locale, entry.fetched_at)}
                <a
                  href={entry.url}
                  className="mt-0.5 block break-all text-cyan underline-offset-4 hover:underline"
                  rel="noreferrer"
                  target="_blank"
                >
                  {entry.url}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </DataRegion>
  );
}

const STAGGER_MS = 110;
const COLUMNS = 3;

function FactFigure({ fact, locale }: { fact: Fact; locale: Locale }) {
  const { t } = useTranslation();
  const presentation = presentationFor(fact.key);
  const figure =
    presentation === undefined ? undefined : figureFor(locale, presentation.figure, fact.params);
  const scale =
    presentation?.scale === undefined
      ? undefined
      : scaleModel(presentation.scale, fact.params, new Date().getUTCFullYear());

  return (
    <>
      {figure !== undefined && (
        <p className="font-display text-figure leading-none font-extralight text-ink tabular-nums">
          {figure.value}
          {figure.unit !== undefined && (
            <span className="ml-2 text-lg font-light text-ink-muted">
              {t(`units.${figure.unit}`)}
            </span>
          )}
        </p>
      )}
      {scale !== undefined && <ScaleBar model={scale} />}
    </>
  );
}

export function FactCard({ fact, index = 0 }: { fact: Fact; index?: number }) {
  const { t } = useTranslation();
  const locale = useLocale();
  const [open, setOpen] = useState(false);
  const [ref, reveal] = useReveal<HTMLElement>();
  const accent = accentFor(fact.module);

  return (
    <article
      ref={ref}
      className={`relative flex flex-col gap-5 border-t border-hairline-strong pt-6 ${REVEAL_CLASS[reveal]}`}
      style={
        {
          '--fact-accent': `var(--hz-mark-${accent})`,
          animationDelay: `${String((index % COLUMNS) * STAGGER_MS)}ms`,
        } as CSSProperties
      }
    >
      <span className="absolute -top-px left-0 h-0.5 w-14 bg-[var(--fact-accent)]" aria-hidden />
      <p className="hz-label flex items-center gap-2.5">
        <span className="size-2 rounded-sm bg-[var(--fact-accent)]" aria-hidden />
        {t(`fact.module.${fact.module}`, { defaultValue: fact.module })}
      </p>
      <FactFigure fact={fact} locale={locale} />
      <p lang={fact.text_lang} className="text-base leading-relaxed text-ink">
        {fact.text}
      </p>
      <details
        className="group mt-auto"
        onToggle={(event) => {
          setOpen(event.currentTarget.open);
        }}
      >
        <summary className="cursor-pointer list-none text-sm text-amber underline-offset-4 hover:underline">
          {t('fact.howWeKnow')}
          <span
            aria-hidden
            className="ml-2 inline-block transition-transform duration-[var(--hz-duration-fast)] group-open:rotate-90"
          >
            ›
          </span>
        </summary>
        <div className="mt-4">{open && <Lineage id={fact.id} />}</div>
      </details>
    </article>
  );
}

export function FactCardPlaceholder() {
  return (
    <div
      className="relative flex min-h-72 flex-col gap-4 overflow-hidden border-t border-hairline pt-6"
      aria-hidden
    >
      <span className="h-2 w-24 rounded-sm bg-surface-raised" />
      <span className="h-12 w-40 rounded-sm bg-surface" />
      <span className="h-px w-full bg-hairline" />
      <span className="h-4 w-full rounded-sm bg-surface" />
      <span className="h-4 w-5/6 rounded-sm bg-surface" />
      <span className="h-4 w-2/3 rounded-sm bg-surface" />
    </div>
  );
}
