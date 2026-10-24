import type { ReactNode } from 'react';
import { PageHeader } from './PageHeader';

interface PageLayoutProps {
  readonly eyebrow?: string;
  readonly title: string;
  readonly lede: string;
  readonly children: ReactNode;
}

export function PageLayout({ eyebrow, title, lede, children }: PageLayoutProps) {
  return (
    <div className="mx-auto max-w-7xl px-gutter pt-16">
      <PageHeader title={title} lede={lede} {...(eyebrow === undefined ? {} : { eyebrow })} />
      {children}
    </div>
  );
}
