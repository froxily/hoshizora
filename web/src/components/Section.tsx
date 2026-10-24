import type { ReactNode } from 'react';

interface SectionProps {
  readonly id: string;
  readonly title: string;
  readonly lede?: string;
  readonly children: ReactNode;
}

export function Section({ id, title, lede, children }: SectionProps) {
  return (
    <section
      aria-labelledby={id}
      className="border-t border-hairline pt-10 pb-section first-of-type:border-t-0"
    >
      <div className="mb-10 max-w-2xl">
        <h2 id={id} className="font-display text-2xl font-light text-ink">
          {title}
        </h2>
        {lede !== undefined && <p className="mt-3 text-ink-muted">{lede}</p>}
      </div>
      {children}
    </section>
  );
}
