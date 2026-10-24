interface PageHeaderProps {
  readonly eyebrow?: string;
  readonly title: string;
  readonly lede: string;
}

export function PageHeader({ eyebrow, title, lede }: PageHeaderProps) {
  return (
    <header className="hz-rise max-w-3xl pt-16 pb-12 sm:pt-24">
      {eyebrow !== undefined && <p className="hz-label mb-6 text-cyan">{eyebrow}</p>}
      <h1 className="font-display text-3xl font-light tracking-display text-ink">{title}</h1>
      <p className="mt-6 text-lg text-ink-muted">{lede}</p>
    </header>
  );
}
