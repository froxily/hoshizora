import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { useDataLink } from '../api/dataLink';
import { factsQuery } from '../api/queries';
import { useDocumentTitle } from '../app/useDocumentTitle';
import { DataLinkPanel } from '../components/DataLink';
import { FactCard, FactCardPlaceholder } from '../components/FactCard';
import { MissionClock } from '../components/MissionClock';
import { HeroBackdrop } from '../hero/HeroBackdrop';
import { useLocale } from '../i18n/useLocale';
import { Ticker } from './home/Ticker';

const HOME_FACTS = 6;

function TopFacts() {
  const { t } = useTranslation();
  const locale = useLocale();
  const link = useDataLink();
  const query = useQuery(factsQuery(locale, { limit: HOME_FACTS }));
  const stalled = link.status === 'waking' || link.status === 'offline' || query.isError;

  return (
    <section aria-labelledby="facts-title" className="mx-auto max-w-7xl px-gutter pt-section">
      <div className="mb-12 max-w-2xl">
        <h2 id="facts-title" className="font-display text-2xl font-light text-ink">
          {t('home.facts.title')}
        </h2>
        <p className="mt-4 text-ink-muted">{t('home.facts.lede')}</p>
      </div>
      {query.data === undefined ? (
        <div className="space-y-10">
          {stalled && (
            <div className="max-w-xl">
              <DataLinkPanel compact />
            </div>
          )}
          <div className="grid items-start gap-x-10 gap-y-14 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: HOME_FACTS }, (_, index) => (
              <FactCardPlaceholder key={index} />
            ))}
          </div>
        </div>
      ) : (
        <div className="grid items-start gap-x-10 gap-y-14 md:grid-cols-2 lg:grid-cols-3">
          {query.data.map((fact, index) => (
            <FactCard key={fact.id} fact={fact} index={index} />
          ))}
        </div>
      )}
    </section>
  );
}

export function HomePage() {
  const { t } = useTranslation();
  useDocumentTitle();

  return (
    <>
      <section className="relative isolate">
        <HeroBackdrop />
        <div className="relative mx-auto grid min-h-svh max-w-7xl grid-rows-[1fr_auto] gap-12 px-gutter pt-28 pb-8">
          <div className="grid content-start gap-14 pt-[5svh] lg:grid-cols-[minmax(0,7fr)_minmax(0,5fr)] lg:gap-16">
            <div>
              <p className="hz-label hz-rise mb-8 text-cyan">{t('home.eyebrow')}</p>
              <h1 className="hz-rise font-display text-hero leading-[1.05] font-extralight tracking-display text-ink [animation-delay:120ms]">
                {t('home.title')}
              </h1>
              <p className="hz-rise mt-8 max-w-2xl text-lg text-ink-muted [animation-delay:240ms]">
                {t('home.lede')}
              </p>
            </div>
            <div className="hz-reveal min-w-0 [animation-delay:360ms] lg:pt-4">
              <Ticker />
            </div>
          </div>
          <div className="hz-fade [animation-delay:480ms]">
            <MissionClock />
          </div>
        </div>
      </section>
      <TopFacts />
    </>
  );
}
