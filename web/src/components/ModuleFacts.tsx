import { useQuery } from '@tanstack/react-query';
import { factsQuery } from '../api/queries';
import { useLocale } from '../i18n/useLocale';
import { FactCard, FactCardPlaceholder } from './FactCard';

interface ModuleFactsProps {
  readonly module?: string;
  readonly entityType?: string;
  readonly entityKey?: string;
  readonly limit?: number;
}

export function ModuleFacts({ module, entityType, entityKey, limit = 3 }: ModuleFactsProps) {
  const locale = useLocale();
  const query = useQuery(
    factsQuery(locale, {
      limit,
      ...(module === undefined ? {} : { module }),
      ...(entityType === undefined ? {} : { entityType }),
      ...(entityKey === undefined ? {} : { entityKey }),
    }),
  );

  if (query.data?.length === 0) {
    return null;
  }

  return (
    <div className="grid items-start gap-x-10 gap-y-14 md:grid-cols-2 lg:grid-cols-3">
      {query.data === undefined
        ? Array.from({ length: limit }, (_, index) => <FactCardPlaceholder key={index} />)
        : query.data.map((fact, index) => <FactCard key={fact.id} fact={fact} index={index} />)}
    </div>
  );
}
